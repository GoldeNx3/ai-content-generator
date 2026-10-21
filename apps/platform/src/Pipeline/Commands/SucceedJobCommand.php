<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class SucceedJobCommand
{
    public function execute(PipelineJob $job, PipelineJobAttempt $attempt, StageResult $result): void
    {
        $now = CarbonImmutable::now();
        $job->forceFill([
            'status' => JobStatus::Succeeded, 'finished_at' => $now, 'lease_expires_at' => null,
            'result_type' => $result->type, 'result_id' => $result->id, 'error_code' => null, 'error_message' => null,
        ])->save();
        $attempt->forceFill(['outcome' => 'succeeded', 'finished_at' => $now])->save();
    }
}
