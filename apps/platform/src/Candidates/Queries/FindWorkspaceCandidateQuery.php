<?php

namespace Modules\Candidates\Queries;

use Modules\Candidates\Models\Candidate;

final class FindWorkspaceCandidateQuery
{
    public function execute(int $id, int $workspaceId): ?Candidate
    {
        return Candidate::query()->whereKey($id)->where('workspace_id', $workspaceId)->first();
    }
}
