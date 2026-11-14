<?php

namespace Modules\Pipeline\Services;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Commands\CancelJobCommand;
use Modules\Pipeline\Commands\RequestJobCancelCommand;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Pipeline\Queries\PendingJobsQuery;
use Modules\Pipeline\Support\ErrorMessages;
use Modules\Shared\Exceptions\ApiException;

final class JobCancellationService
{
    public function __construct(
        private readonly CancelJobCommand $cancelJob,
        private readonly RequestJobCancelCommand $requestCancel,
        private readonly PendingJobsQuery $pending,
        private readonly HandlerRegistry $handlers,
    ) {}

    public function cancel(PipelineJob $job, ?int $userId): PipelineJob
    {
        return DB::transaction(function () use ($job, $userId): PipelineJob {
            $locked = PipelineJob::query()->whereKey($job->id)->lockForUpdate()->firstOrFail();
            match ($locked->status) {
                JobStatus::Queued, JobStatus::Retrying => $this->cancelWaiting($locked, $userId),
                JobStatus::Running => $this->requestCancel->execute($locked, $userId),
                default => throw new ApiException('job_not_cancellable', 409),
            };

            return $locked;
        });
    }

    public function cancelPending(int $workspaceId, ?int $userId): int
    {
        return DB::transaction(function () use ($workspaceId, $userId): int {
            $jobs = $this->pending->execute($workspaceId);
            foreach ($jobs as $job) {
                $this->cancelWaiting($job, $userId);
            }

            return $jobs->count();
        });
    }

    public function cancelRunning(PipelineJob $locked, PipelineJobAttempt $attempt): void
    {
        $this->cancelJob->execute($locked, $attempt, null);
        $this->handlers->for($locked->kind)->failed($locked, true, ErrorMessages::for('cancelled'), null);
    }

    private function cancelWaiting(PipelineJob $locked, ?int $userId): void
    {
        $this->cancelJob->execute($locked, null, $userId);
        $this->handlers->for($locked->kind)->failed($locked, true, ErrorMessages::for('cancelled'), null);
    }
}
