<?php

namespace Modules\Pipeline\Queries;

use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class JobStatsQuery
{
    public function execute(int $workspaceId): array
    {
        $counts = PipelineJob::query()
            ->where('workspace_id', $workspaceId)
            ->groupBy('status')
            ->selectRaw('status, COUNT(*) AS total')
            ->toBase()
            ->pluck('total', 'status');
        $stats = [];
        foreach (JobStatus::cases() as $status) {
            $stats[$status->value] = (int) ($counts[$status->value] ?? 0);
        }

        return [...$stats, 'total' => array_sum($stats)];
    }
}
