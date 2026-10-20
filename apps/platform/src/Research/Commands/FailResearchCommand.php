<?php

namespace Modules\Research\Commands;

use Carbon\CarbonImmutable;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;

final class FailResearchCommand
{
    public function execute(string $jobId, string $message): void
    {
        Research::query()->where('job_id', $jobId)->update([
            'status' => ResearchStatus::Failed, 'error' => $message, 'completed_at' => CarbonImmutable::now(),
        ]);
    }
}
