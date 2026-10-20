<?php

namespace Modules\Pipeline\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Exceptions\LeaseLostException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class UpdateRunningJobCommand
{
    public function stage(PipelineJob $job, string $stage): void
    {
        $this->fenced($job, function (PipelineJob $locked, PipelineJobAttempt $attempt) use ($stage): void {
            $locked->forceFill(['stage' => $stage])->save();
            $attempt->forceFill(['last_stage' => $stage])->save();
        });
        $job->stage = $stage;
    }

    public function calls(PipelineJob $job, array $calls): void
    {
        if ($calls === []) {
            return;
        }
        $this->fenced($job, function (PipelineJob $locked, PipelineJobAttempt $attempt) use ($calls): void {
            $attempt->forceFill(['llm_calls' => [...($attempt->llm_calls ?? []), ...$calls]])->save();
        });
    }

    public function checkpoint(PipelineJob $job, string $key, mixed $value): void
    {
        $this->fenced($job, function (PipelineJob $locked) use ($key, $value): void {
            $locked->forceFill(['checkpoints' => [...($locked->checkpoints ?? []), $key => $value]])->save();
        });
        $job->checkpoints = [...($job->checkpoints ?? []), $key => $value];
    }

    public function fenced(PipelineJob $job, callable $write): mixed
    {
        return DB::transaction(function () use ($job, $write) {
            $locked = PipelineJob::query()->whereKey($job->id)->lockForUpdate()->firstOrFail();
            if ($locked->status !== JobStatus::Running || $locked->attempt_count !== $job->attempt_count) {
                throw new LeaseLostException("Job {$job->id} is no longer owned by this attempt.");
            }
            $attempt = PipelineJobAttempt::query()
                ->where('pipeline_job_id', $job->id)->where('number', $job->attempt_count)->firstOrFail();

            return $write($locked, $attempt);
        });
    }
}
