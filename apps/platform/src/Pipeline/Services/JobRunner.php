<?php

namespace Modules\Pipeline\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Modules\Ai\Services\AiRunner;
use Modules\Pipeline\Commands\ClaimJobCommand;
use Modules\Pipeline\Commands\FailJobCommand;
use Modules\Pipeline\Commands\SucceedJobCommand;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Exceptions\JobCancelledException;
use Modules\Pipeline\Exceptions\LeaseLostException;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Pipeline\Support\ErrorMessages;
use Throwable;

final class JobRunner
{
    private const LEASE_GRACE_SECONDS = 120;

    public function __construct(
        private readonly ClaimJobCommand $claim,
        private readonly RunningJobWriter $update,
        private readonly SucceedJobCommand $succeed,
        private readonly FailJobCommand $failJob,
        private readonly HandlerRegistry $handlers,
        private readonly FailurePolicy $policy,
        private readonly AiRunner $ai,
        private readonly JobCancellationService $cancellation,
    ) {}

    public function run(string $jobId): void
    {
        $timeouts = config('content.jobs.timeouts');
        $kind = PipelineJob::query()->whereKey($jobId)->toBase()->value('kind');
        if ($kind === null) {
            return;
        }
        $timeout = (int) ($timeouts[$kind] ?? 900);
        $job = $this->claim->execute($jobId, $timeout + self::LEASE_GRACE_SECONDS);
        if ($job === null) {
            return;
        }
        $context = new JobRunContext($job, $this->update, $this->succeed, $this->ai, $timeout);
        try {
            $this->handlers->for($job->kind)->run($job, $context);
        } catch (JobCancelledException) {
            try {
                $this->update->fenced($job, fn (PipelineJob $locked, PipelineJobAttempt $attempt) => $this->cancellation->cancelRunning($locked, $attempt));
            } catch (LeaseLostException) {
                Log::warning('Pipeline job lease lost while saving cancellation', ['job_id' => $job->id]);
            }
        } catch (LeaseLostException $exception) {
            Log::warning('Pipeline job lease lost', ['job_id' => $job->id, 'error' => $exception->getMessage()]);
        } catch (Throwable $exception) {
            Log::error('Pipeline job failed', ['job_id' => $job->id, 'kind' => $job->kind->value, 'exception' => $exception]);
            $this->fail($job, $exception, fenced: true);
        }
    }

    public function interrupted(string $jobId): void
    {
        $job = PipelineJob::query()->find($jobId);
        if ($job !== null && $job->status === JobStatus::Running) {
            $this->recordFailure($job, 'worker_interrupted', ErrorMessages::for('worker_interrupted'), true, null, null, 'interrupted');
        }
    }

    public function recoverLost(PipelineJob $job): void
    {
        $this->recordFailure($job, 'worker_lost', ErrorMessages::for('worker_lost'), true, null, null, 'interrupted');
    }

    private function fail(PipelineJob $job, Throwable $exception, bool $fenced): void
    {
        [$code, $message, $retryable, $retryAfter, $details] = $this->policy->describe($exception);
        try {
            $this->recordFailure($job, $code, $message, $retryable, $retryAfter, $details, null, $fenced);
        } catch (LeaseLostException) {
            Log::warning('Pipeline job lease lost while saving failure', ['job_id' => $job->id]);
        }
    }

    private function recordFailure(PipelineJob $job, string $code, string $message, bool $retryable, ?float $retryAfter, ?array $details, ?string $outcome, bool $fenced = false): void
    {
        $retry = false;
        $write = function (PipelineJob $locked, ?PipelineJobAttempt $attempt) use ($code, $message, $retryable, $retryAfter, $details, $outcome, &$retry): void {
            $retry = $retryable && $locked->attempt_count < $locked->max_attempts;
            $available = CarbonImmutable::now()->addSeconds($this->policy->delaySeconds($locked->attempt_count, $retryAfter));
            $this->failJob->execute($locked, $attempt, $retry, $code, $message, $available, $outcome ?? ($retry ? 'retryable_error' : 'failed'));
            $this->handlers->for($locked->kind)->failed($locked, ! $retry, $message, $details);
        };
        if ($fenced) {
            $this->update->fenced($job, fn (PipelineJob $locked, PipelineJobAttempt $attempt) => $write($locked, $attempt));
        } else {
            DB::transaction(function () use ($job, $write): void {
                $locked = PipelineJob::query()->whereKey($job->id)->lockForUpdate()->firstOrFail();
                if ($locked->status !== JobStatus::Running) {
                    return;
                }
                $attempt = PipelineJobAttempt::query()->where('pipeline_job_id', $locked->id)->where('number', $locked->attempt_count)->first();
                $write($locked, $attempt);
            });
        }
        $fresh = $job->fresh();
        if ($retry && $fresh !== null && $fresh->status === JobStatus::Retrying) {
            RunPipelineJob::dispatch($fresh->id, $fresh->kind->value)->delay($fresh->available_at);
        }
    }
}
