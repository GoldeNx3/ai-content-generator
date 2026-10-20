<?php

namespace Modules\Classification\Queries;

use Modules\Candidates\Models\Candidate;

final class WorkspacesWithPendingClassificationQuery
{
    public function execute(): array
    {
        return Candidate::query()
            ->whereNull('total_score')
            ->where('external_url', 'not like', Candidate::DEMO_PREFIX.'%')
            ->distinct()
            ->orderBy('workspace_id')
            ->pluck('workspace_id')
            ->all();
    }
}
