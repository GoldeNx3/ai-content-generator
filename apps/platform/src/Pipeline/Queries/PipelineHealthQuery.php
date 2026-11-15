<?php

namespace Modules\Pipeline\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class PipelineHealthQuery
{
    public function execute(CarbonImmutable $now, int $stallMinutes, int $runningMinutes, int $errorWindowMinutes): array
    {
        $stalled = DB::table('pipeline_jobs')
            ->join('workspaces', 'workspaces.id', '=', 'pipeline_jobs.workspace_id')
            ->whereNull('workspaces.paused_at')
            ->where('pipeline_jobs.status', 'queued')
            ->where('pipeline_jobs.available_at', '<', $now->subMinutes($stallMinutes))
            ->selectRaw('COUNT(*) AS jobs, MIN(pipeline_jobs.available_at) AS oldest')
            ->first();
        $running = DB::table('pipeline_jobs')->where('status', 'running')->where('started_at', '<', $now->subMinutes($runningMinutes))->count();
        $errors = DB::table('pipeline_job_attempts')
            ->where('outcome', 'retryable_error')
            ->where('finished_at', '>=', $now->subMinutes($errorWindowMinutes))
            ->groupBy('error_code')
            ->selectRaw('error_code, COUNT(*) AS attempts')
            ->orderByDesc('attempts')
            ->pluck('attempts', 'error_code')
            ->map(fn ($count) => (int) $count)
            ->all();

        return [
            'stalled' => (int) $stalled->jobs,
            'oldest' => $stalled->oldest === null ? null : CarbonImmutable::parse($stalled->oldest),
            'running' => $running,
            'errors' => $errors,
        ];
    }
}
