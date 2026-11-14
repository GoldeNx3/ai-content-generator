<?php

namespace Modules\Pipeline\Commands;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Models\PipelineJob;

final class RequestJobCancelCommand
{
    public function execute(PipelineJob $locked, ?int $userId): void
    {
        $locked->forceFill(['cancel_requested_at' => CarbonImmutable::now(), 'cancelled_by' => $userId])->save();
    }
}
