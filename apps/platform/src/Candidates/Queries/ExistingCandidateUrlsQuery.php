<?php

namespace Modules\Candidates\Queries;

use Modules\Candidates\Models\Candidate;

final class ExistingCandidateUrlsQuery
{
    public function execute(int $workspaceId, array $urls): array
    {
        if ($urls === []) {
            return [];
        }

        return Candidate::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('external_url', $urls)
            ->pluck('external_url')
            ->all();
    }
}
