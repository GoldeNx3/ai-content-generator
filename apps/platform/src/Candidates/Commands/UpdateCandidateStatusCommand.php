<?php

namespace Modules\Candidates\Commands;

use Modules\Candidates\Enums\CandidateStatus;
use Modules\Candidates\Models\Candidate;

final class UpdateCandidateStatusCommand
{
    public function execute(Candidate $candidate, CandidateStatus $status): void
    {
        $candidate->update(['status' => $status]);
    }
}
