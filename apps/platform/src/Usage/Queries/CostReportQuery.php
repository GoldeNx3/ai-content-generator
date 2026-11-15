<?php

namespace Modules\Usage\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Database\Query\Builder;
use Illuminate\Support\Facades\DB;

final class CostReportQuery
{
    private const COST = "COALESCE(SUM((call->>'estimated_cost_usd')::numeric), 0)";

    public function execute(int $workspaceId, CarbonImmutable $from, CarbonImmutable $to): array
    {
        $calls = fn (): Builder => DB::table('pipeline_job_attempts as attempt')
            ->join('pipeline_jobs as job', 'job.id', '=', 'attempt.pipeline_job_id')
            ->crossJoin(DB::raw('jsonb_array_elements(attempt.llm_calls) AS call'))
            ->where('job.workspace_id', $workspaceId)
            ->where('attempt.started_at', '>=', $from)
            ->where('attempt.started_at', '<', $to);

        return [
            'total' => $calls()->selectRaw(self::COST.' AS cost')
                ->selectRaw("COUNT(*) FILTER (WHERE call->>'estimated_cost_usd' IS NULL AND call->>'finished' = 'false') AS unknown")->first(),
            'kinds' => $calls()->groupBy('job.kind')->select('job.kind')->selectRaw('COUNT(DISTINCT job.id) AS jobs')
                ->selectRaw(self::COST.' AS cost')->orderByRaw('cost DESC')->get()->all(),
            'stages' => $calls()->groupByRaw("call->>'stage'")->selectRaw("call->>'stage' AS stage")->selectRaw('COUNT(*) AS calls')
                ->selectRaw(self::COST.' AS cost')->orderByRaw('cost DESC')->get()->all(),
            'articles' => $calls()->whereExists(fn (Builder $query) => $query->from('articles')->whereColumn('articles.candidate_id', 'job.candidate_id'))
                ->selectRaw('COUNT(DISTINCT job.candidate_id) AS topics')->selectRaw(self::COST.' AS cost')->first(),
        ];
    }
}
