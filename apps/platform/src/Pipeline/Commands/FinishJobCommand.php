<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class FinishJobCommand
{
    public function succeed(PipelineJob $job, PipelineJobAttempt $attempt, StageResult $result): void
    {
        $now = CarbonImmutable::now();
        $job->forceFill([
            'status' => JobStatus::Succeeded, 'finished_at' => $now, 'lease_expires_at' => null,
            'result_type' => $result->type, 'result_id' => $result->id, 'error_code' => null, 'error_message' => null,
        ])->save();
        $attempt->forceFill(['outcome' => 'succeeded', 'finished_at' => $now])->save();
    }

    public function fail(PipelineJob $job, ?PipelineJobAttempt $attempt, bool $retry, string $code, string $message, CarbonImmutable $availableAt, string $outcome): void
    {
        $now = CarbonImmutable::now();
        $job->forceFill([
            'status' => $retry ? JobStatus::Retrying : JobStatus::Failed,
            'error_code' => $code,
            'error_message' => $message,
            'available_at' => $availableAt,
            'finished_at' => $retry ? null : $now,
            'lease_expires_at' => null,
        ])->save();
        $attempt?->forceFill([
            'outcome' => $outcome, 'finished_at' => $now, 'error_code' => $code, 'error_message' => $message,
            'last_stage' => $job->stage,
        ])->save();
    }
}
