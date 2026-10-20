<?php

namespace Modules\Usage\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class WorkspaceSpendQuery
{
    public function execute(int $workspaceId, CarbonImmutable $since): array
    {
        $row = DB::table('pipeline_job_attempts as attempt')
            ->join('pipeline_jobs as job', 'job.id', '=', 'attempt.pipeline_job_id')
            ->crossJoin(DB::raw('jsonb_array_elements(attempt.llm_calls) AS call'))
            ->where('job.workspace_id', $workspaceId)
            ->where('attempt.started_at', '>=', $since)
            ->selectRaw("COALESCE(SUM((call->>'estimated_cost_usd')::numeric), 0) AS spent")
            ->selectRaw("COUNT(*) FILTER (WHERE call->>'estimated_cost_usd' IS NULL AND call->>'finished' = 'false') AS unknown")
            ->first();

        return [number_format((float) $row->spent, 6, '.', ''), (int) $row->unknown];
    }
}
