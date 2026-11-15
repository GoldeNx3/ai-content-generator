<?php

namespace Modules\Demo\Queries;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;

final class DemoCandidateIdsQuery
{
    /** @return list<int> */
    public function execute(int $workspaceId): array
    {
        return DB::table('candidates')
            ->where('workspace_id', $workspaceId)
            ->where('external_url', 'like', Candidate::DEMO_PREFIX.'%')
            ->lockForUpdate()
            ->pluck('id')
            ->map(fn ($id) => (int) $id)
            ->all();
    }
}
