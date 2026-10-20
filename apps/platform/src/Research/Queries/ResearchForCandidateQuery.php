<?php

namespace Modules\Research\Queries;

use Modules\Research\Models\Research;

final class ResearchForCandidateQuery
{
    public function execute(int $candidateId, bool $withRelations = true): ?Research
    {
        return Research::query()
            ->when($withRelations, fn ($query) => $query->with(['sources', 'facts.sources']))
            ->where('candidate_id', $candidateId)
            ->first();
    }
}
