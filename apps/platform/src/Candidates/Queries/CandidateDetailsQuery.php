<?php

namespace Modules\Candidates\Queries;

use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Support\WorkflowStatusExpression;

final class CandidateDetailsQuery
{
    public function execute(int $candidateId): Candidate
    {
        return Candidate::query()
            ->select('candidates.*', 'sources.name as source_name')
            ->selectRaw(WorkflowStatusExpression::sql().' as workflow_status')
            ->selectRaw('1 + (SELECT COUNT(*) FROM candidates AS members WHERE members.topic_group_id = candidates.id) AS group_size')
            ->join('sources', 'sources.id', '=', 'candidates.source_id')
            ->where('candidates.id', $candidateId)
            ->firstOrFail();
    }
}
