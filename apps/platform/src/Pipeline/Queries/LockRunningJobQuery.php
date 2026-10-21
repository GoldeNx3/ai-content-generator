<?php

namespace Modules\Pipeline\Queries;

use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Exceptions\LeaseLostException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class LockRunningJobQuery
{
    public function execute(PipelineJob $job): array
    {
        $locked = PipelineJob::query()->whereKey($job->id)->lockForUpdate()->firstOrFail();
        if ($locked->status !== JobStatus::Running || $locked->attempt_count !== $job->attempt_count) {
            throw new LeaseLostException("Job {$job->id} is no longer owned by this attempt.");
        }
        $attempt = PipelineJobAttempt::query()->where('pipeline_job_id', $job->id)->where('number', $job->attempt_count)->firstOrFail();

        return [$locked, $attempt];
    }
}
