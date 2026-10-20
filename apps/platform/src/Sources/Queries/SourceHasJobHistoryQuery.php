<?php

namespace Modules\Sources\Queries;

use Illuminate\Support\Facades\DB;

final class SourceHasJobHistoryQuery
{
    public function execute(int $sourceId): bool
    {
        return DB::table('pipeline_jobs')
            ->join('candidates', 'candidates.id', '=', 'pipeline_jobs.candidate_id')
            ->where('candidates.source_id', $sourceId)
            ->exists();
    }
}
