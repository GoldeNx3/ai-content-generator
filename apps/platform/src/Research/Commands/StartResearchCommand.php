<?php

namespace Modules\Research\Commands;

use Carbon\CarbonImmutable;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Enums\SourceOrigin;
use Modules\Research\Models\Research;
use Modules\Research\Models\ResearchFact;
use Modules\Research\Models\ResearchSource;

final class StartResearchCommand
{
    public function execute(int $candidateId, string $jobId, bool $discover): Research
    {
        $research = Research::query()->firstOrNew(['candidate_id' => $candidateId]);
        $attributes = [
            'job_id' => $jobId, 'status' => ResearchStatus::Running, 'summary' => null, 'why_it_matters' => null,
            'suggested_angle' => null, 'uncertainties' => [], 'conflicts' => [], 'error' => null,
            'started_at' => CarbonImmutable::now(), 'completed_at' => null, 'llm_model' => null,
            'llm_input_tokens' => 0, 'llm_output_tokens' => 0, 'estimated_cost_usd' => null,
        ];
        if ($discover) {
            $attributes['search_queries'] = [];
        }
        $research->fill($attributes)->save();
        ResearchFact::query()->where('research_id', $research->id)->delete();
        if ($discover) {
            ResearchSource::query()->where('research_id', $research->id)->where('origin', '!=', SourceOrigin::Manual->value)->delete();
        }

        return $research;
    }
}
