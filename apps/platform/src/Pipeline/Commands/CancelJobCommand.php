<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Pipeline\Support\ErrorMessages;

final class CancelJobCommand
{
    public function execute(PipelineJob $locked, ?PipelineJobAttempt $attempt, ?int $userId): void
    {
        $now = CarbonImmutable::now();
        $message = ErrorMessages::for('cancelled');
        $locked->forceFill([
            'status' => JobStatus::Cancelled, 'error_code' => 'cancelled', 'error_message' => $message,
            'finished_at' => $now, 'lease_expires_at' => null, 'cancelled_by' => $locked->cancelled_by ?? $userId,
            'cancel_requested_at' => $locked->cancel_requested_at ?? $now,
        ])->save();
        $attempt?->forceFill([
            'outcome' => 'cancelled', 'finished_at' => $now, 'error_code' => 'cancelled', 'error_message' => $message, 'last_stage' => $locked->stage,
        ])->save();
    }
}
