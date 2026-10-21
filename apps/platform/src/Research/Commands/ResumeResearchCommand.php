<?php

namespace Modules\Research\Commands;

use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;
use Modules\Research\Models\ResearchFact;

final class ResumeResearchCommand
{
    public function execute(int $researchId): Research
    {
        ResearchFact::query()->where('research_id', $researchId)->delete();
        $research = Research::query()->findOrFail($researchId);
        $research->update(['status' => ResearchStatus::Running]);

        return $research;
    }
}
