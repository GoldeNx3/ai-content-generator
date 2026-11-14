<?php

namespace Modules\Pipeline\Services;

use Illuminate\Support\Facades\DB;
use Modules\Ai\Exceptions\AiTaskException;
use Modules\Ai\Services\AiRunner;
use Modules\Pipeline\Commands\SucceedJobCommand;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Exceptions\JobCancelledException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class JobRunContext
{
    public function __construct(
        public readonly PipelineJob $job,
        private readonly RunningJobWriter $update,
        private readonly SucceedJobCommand $succeed,
        private readonly AiRunner $ai,
        private readonly int $timeoutSeconds,
    ) {}

    public function stage(string $stage): void
    {
        $this->update->stage($this->job, $stage);
    }

    public function checkpoint(string $key, mixed $value): void
    {
        $this->update->checkpoint($this->job, $key, $value);
    }

    public function checkpointValue(string $key): mixed
    {
        return $this->job->checkpoint($key);
    }

    public function ai(string $step, string $task, array $input): array
    {
        if (PipelineJob::query()->whereKey($this->job->id)->value('cancel_requested_at') !== null) {
            throw new JobCancelledException("Job {$this->job->id} was cancelled.");
        }
        $cached = $this->checkpointValue('ai:'.$step);
        if ($cached !== null) {
            return $cached;
        }
        try {
            $response = $this->ai->run($task, $input, (bool) ($this->job->payload['demo'] ?? false), $this->timeoutSeconds);
        } catch (AiTaskException $exception) {
            $this->update->calls($this->job, $exception->calls);
            throw $exception;
        }
        $checkpoint = ['result' => $response->result, 'calls' => $response->calls];
        $this->update->aiResult($this->job, 'ai:'.$step, $checkpoint);

        return $checkpoint;
    }

    public function finish(callable $persist): void
    {
        $this->update->fenced($this->job, function (PipelineJob $locked, PipelineJobAttempt $attempt) use ($persist): void {
            $result = $persist() ?? new StageResult;
            $this->succeed->execute($locked, $attempt, $result);
        });
    }

    public function transaction(callable $write): mixed
    {
        return $this->update->fenced($this->job, fn () => DB::transaction($write));
    }
}
