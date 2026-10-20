<?php

namespace Modules\Pipeline\Queries;

use Modules\Candidates\Models\Candidate;

final class LockCandidateQuery
{
    public function execute(int $candidateId): Candidate
    {
        return Candidate::query()->with('source')->whereKey($candidateId)->lockForUpdate()->firstOrFail();
    }
}
