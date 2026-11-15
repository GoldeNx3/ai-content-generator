<?php

namespace Modules\Demo\Queries;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Enums\JobStatus;

final class DemoHasActiveJobsQuery
{
    /** @param list<int> $candidateIds */
    public function execute(int $workspaceId, array $candidateIds): bool
    {
        return $candidateIds !== [] && DB::table('pipeline_jobs')
            ->where('workspace_id', $workspaceId)
            ->whereIn('candidate_id', $candidateIds)
            ->whereIn('status', [JobStatus::Queued->value, JobStatus::Running->value, JobStatus::Retrying->value])
            ->exists();
    }
}
