<?php

namespace Modules\Research\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Support\CallUsage;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;
use Modules\Research\Models\ResearchFact;
use Modules\Research\Models\ResearchSource;

final class SaveResearchAnalysisCommand
{
    public function execute(Research $research, array $analysis, CallUsage $usage): void
    {
        ResearchFact::query()->where('research_id', $research->id)->delete();
        $known = ResearchSource::query()->where('research_id', $research->id)->pluck('id')->flip();
        foreach ($analysis['facts'] as $fact) {
            $created = ResearchFact::query()->create([
                'research_id' => $research->id, 'claim' => $fact['claim'], 'importance' => $fact['importance'],
                'confidence' => $fact['confidence'], 'basis' => $fact['basis'] ?? null,
            ]);
            $links = array_values(array_filter($fact['source_ids'], fn ($id) => $known->has($id)));
            DB::table('research_fact_sources')->insert(array_map(fn ($id) => ['fact_id' => $created->id, 'source_id' => $id], $links));
        }
        foreach ($analysis['source_updates'] as $update) {
            ResearchSource::query()->where('research_id', $research->id)->whereKey($update['id'])->update([
                'source_type' => $update['source_type'], 'source_score' => $update['source_score'], 'publisher' => $update['publisher'],
            ]);
        }
        $research->update([
            'status' => ResearchStatus::Completed,
            'summary' => $analysis['summary'],
            'why_it_matters' => $analysis['why_it_matters'],
            'suggested_angle' => $analysis['suggested_angle'],
            'uncertainties' => $analysis['uncertainties'],
            'conflicts' => $analysis['conflicts'],
            'error' => null,
            'llm_model' => $usage->model,
            'llm_input_tokens' => $usage->inputTokens,
            'llm_output_tokens' => $usage->outputTokens,
            'estimated_cost_usd' => $usage->costUsd,
            'completed_at' => CarbonImmutable::now(),
        ]);
    }
}
