<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class ClaimJobCommand
{
    public function execute(string $jobId, int $leaseSeconds): ?PipelineJob
    {
        return DB::transaction(function () use ($jobId, $leaseSeconds): ?PipelineJob {
            $now = CarbonImmutable::now();
            $job = PipelineJob::query()->whereKey($jobId)
                ->whereIn('status', [JobStatus::Queued->value, JobStatus::Retrying->value])
                ->lockForUpdate()
                ->first();
            if ($job === null) {
                return null;
            }
            $job->forceFill([
                'status' => JobStatus::Running,
                'attempt_count' => $job->attempt_count + 1,
                'started_at' => $job->started_at ?? $now,
                'lease_expires_at' => $now->addSeconds($leaseSeconds),
            ])->save();
            PipelineJobAttempt::query()->create([
                'pipeline_job_id' => $job->id, 'number' => $job->attempt_count, 'started_at' => $now,
            ]);

            return $job;
        });
    }
}
