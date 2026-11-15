<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\EditorialSuggestion;

final class CandidateSuggestionsQuery
{
    public function execute(int $candidateId): array
    {
        return EditorialSuggestion::query()->where('candidate_id', $candidateId)->orderBy('id')->get()->all();
    }
}
