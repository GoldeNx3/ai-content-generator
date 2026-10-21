<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class FailJobCommand
{
    public function execute(PipelineJob $job, ?PipelineJobAttempt $attempt, bool $retry, string $code, string $message, CarbonImmutable $availableAt, string $outcome): void
    {
        $now = CarbonImmutable::now();
        $job->forceFill([
            'status' => $retry ? JobStatus::Retrying : JobStatus::Failed, 'error_code' => $code, 'error_message' => $message,
            'available_at' => $availableAt, 'finished_at' => $retry ? null : $now, 'lease_expires_at' => null,
        ])->save();
        $attempt?->forceFill([
            'outcome' => $outcome, 'finished_at' => $now, 'error_code' => $code, 'error_message' => $message, 'last_stage' => $job->stage,
        ])->save();
    }
}
