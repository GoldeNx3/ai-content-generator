<?php

namespace Modules\Candidates\Queries;

use Modules\Candidates\Models\Candidate;

final class CandidateDetailsQuery
{
    public function execute(int $candidateId): Candidate
    {
        return Candidate::query()
            ->select('candidates.*', 'sources.name as source_name')
            ->selectRaw(WorkflowStatusExpression::sql().' as workflow_status')
            ->join('sources', 'sources.id', '=', 'candidates.source_id')
            ->where('candidates.id', $candidateId)
            ->firstOrFail();
    }
}
