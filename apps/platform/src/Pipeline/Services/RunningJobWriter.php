<?php

namespace Modules\Pipeline\Services;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Commands\AppendAttemptCallsCommand;
use Modules\Pipeline\Commands\SaveJobCheckpointCommand;
use Modules\Pipeline\Commands\SetJobStageCommand;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Pipeline\Queries\LockRunningJobQuery;

final class RunningJobWriter
{
    public function __construct(
        private readonly LockRunningJobQuery $lock,
        private readonly SetJobStageCommand $setStage,
        private readonly AppendAttemptCallsCommand $appendCalls,
        private readonly SaveJobCheckpointCommand $saveCheckpoint,
    ) {}

    public function stage(PipelineJob $job, string $stage): void
    {
        $this->fenced($job, fn (PipelineJob $locked, PipelineJobAttempt $attempt) => $this->setStage->execute($locked, $attempt, $stage));
        $job->stage = $stage;
    }

    public function calls(PipelineJob $job, array $calls): void
    {
        if ($calls !== []) {
            $this->fenced($job, fn (PipelineJob $locked, PipelineJobAttempt $attempt) => $this->appendCalls->execute($attempt, $calls));
        }
    }

    public function checkpoint(PipelineJob $job, string $key, mixed $value): void
    {
        $this->fenced($job, fn (PipelineJob $locked) => $this->saveCheckpoint->execute($locked, $key, $value));
        $job->checkpoints = [...($job->checkpoints ?? []), $key => $value];
    }

    public function aiResult(PipelineJob $job, string $key, array $checkpoint): void
    {
        $this->fenced($job, function (PipelineJob $locked, PipelineJobAttempt $attempt) use ($key, $checkpoint): void {
            $this->appendCalls->execute($attempt, $checkpoint['calls']);
            $this->saveCheckpoint->execute($locked, $key, $checkpoint);
        });
        $job->checkpoints = [...($job->checkpoints ?? []), $key => $checkpoint];
    }

    public function fenced(PipelineJob $job, callable $write): mixed
    {
        return DB::transaction(function () use ($job, $write) {
            [$locked, $attempt] = $this->lock->execute($job);

            return $write($locked, $attempt);
        });
    }
}
