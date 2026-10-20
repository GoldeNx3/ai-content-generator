<?php

namespace Modules\Candidates\Queries;

use Carbon\CarbonImmutable;
use Modules\Candidates\Data\DashboardStatsData;
use Modules\Candidates\Models\Candidate;

final class DashboardStatsQuery
{
    public function execute(int $workspaceId): DashboardStatsData
    {
        $today = CarbonImmutable::now('UTC')->startOfDay();
        $row = Candidate::query()
            ->where('workspace_id', $workspaceId)
            ->selectRaw('COUNT(*) FILTER (WHERE created_at >= ?) AS candidates_today', [$today])
            ->selectRaw("COUNT(*) FILTER (WHERE created_at >= ? AND status = 'pending') AS new_today", [$today])
            ->selectRaw("COUNT(*) FILTER (WHERE status = 'approved') AS approved")
            ->selectRaw("COUNT(*) FILTER (WHERE status = 'ignored') AS ignored")
            ->selectRaw('AVG(total_score) AS average_score')
            ->toBase()
            ->first();

        return new DashboardStatsData(
            (int) $row->candidates_today, (int) $row->new_today, (int) $row->approved, (int) $row->ignored,
            $row->average_score === null ? null : round((float) $row->average_score, 1),
        );
    }
}
