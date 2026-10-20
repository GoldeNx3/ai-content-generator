<?php

namespace Modules\Classification\Queries;

use Modules\Candidates\Models\Candidate;

final class UnclassifiedCandidatesQuery
{
    public function execute(int $workspaceId, int $limit, bool $withoutClassifyHistory = false): array
    {
        return Candidate::query()
            ->where('workspace_id', $workspaceId)
            ->whereNull('total_score')
            ->where('external_url', 'not like', Candidate::DEMO_PREFIX.'%')
            ->when($withoutClassifyHistory, fn ($query) => $query->whereNotExists(fn ($sub) => $sub
                ->selectRaw('1')->from('pipeline_jobs')
                ->whereColumn('pipeline_jobs.candidate_id', 'candidates.id')
                ->where('pipeline_jobs.kind', 'classify')))
            ->orderByRaw('original_published_at DESC NULLS LAST')
            ->orderByDesc('id')
            ->limit($limit)
            ->pluck('id')
            ->all();
    }
}
