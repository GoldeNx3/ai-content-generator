<?php

namespace Modules\Candidates\Queries;

use Modules\Candidates\Models\Candidate;

final class ExistingCandidateUrlKeysQuery
{
    public function execute(int $workspaceId, array $keys): array
    {
        if ($keys === []) {
            return [];
        }

        return Candidate::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('url_key', $keys)
            ->pluck('url_key')
            ->all();
    }
}
