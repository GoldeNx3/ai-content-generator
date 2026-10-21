<?php

namespace Modules\Research\Commands;

use Modules\Research\Models\Research;

final class FindOrCreateResearchCommand
{
    public function execute(int $candidateId): Research
    {
        return Research::query()->firstOrCreate(['candidate_id' => $candidateId]);
    }
}
