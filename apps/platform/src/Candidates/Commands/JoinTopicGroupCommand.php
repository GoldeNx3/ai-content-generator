<?php

namespace Modules\Candidates\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;

final class JoinTopicGroupCommand
{
    public function execute(int $candidateId, Candidate $primary): void
    {
        DB::table('candidates')->where('id', $candidateId)->update([
            'topic_group_id' => $primary->id,
            'duplicate_similarity' => null,
            'relevance_score' => $primary->relevance_score,
            'freshness_score' => $primary->freshness_score,
            'search_potential_score' => $primary->search_potential_score,
            'commercial_potential_score' => $primary->commercial_potential_score,
            'total_score' => $primary->total_score,
            'category' => $primary->category?->value,
            'covered_by' => $primary->covered_by === null ? null : json_encode($primary->covered_by, JSON_THROW_ON_ERROR),
            'llm_reason' => sprintf('Ręcznie połączono z tematem #%d „%s”. Ocena przejęta bez ponownej klasyfikacji.', $primary->id, $primary->title),
            'classified_at' => CarbonImmutable::now(),
            'updated_at' => CarbonImmutable::now(),
        ]);
    }
}
