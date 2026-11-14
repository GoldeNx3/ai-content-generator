<?php

namespace Modules\Pipeline\Queries;

use Modules\Candidates\Models\Candidate;

final class CandidateWorkspaceQuery
{
    public function execute(int $candidateId): ?int
    {
        $workspaceId = Candidate::query()->whereKey($candidateId)->value('workspace_id');

        return $workspaceId === null ? null : (int) $workspaceId;
    }
}
