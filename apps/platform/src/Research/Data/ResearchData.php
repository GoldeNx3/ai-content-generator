<?php

namespace Modules\Research\Data;

use Carbon\CarbonImmutable;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;
use Spatie\LaravelData\Data;

final class ResearchData extends Data
{
    public function __construct(
        public int $id,
        public int $candidate_id,
        public ResearchStatus $status,
        public ?string $summary,
        public ?string $why_it_matters,
        public ?string $suggested_angle,
        public array $search_queries,
        public array $uncertainties,
        public array $conflicts,
        public ?string $error,
        public ?string $llm_model,
        public int $llm_input_tokens,
        public int $llm_output_tokens,
        public ?string $estimated_cost_usd,
        public ?CarbonImmutable $started_at,
        public ?CarbonImmutable $completed_at,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
        public array $sources,
        public array $facts,
    ) {}

    public static function fromModel(Research $research): self
    {
        return new self(
            $research->id, $research->candidate_id, $research->status, $research->summary, $research->why_it_matters,
            $research->suggested_angle, $research->search_queries ?? [], $research->uncertainties ?? [],
            $research->conflicts ?? [], $research->error, $research->llm_model, $research->llm_input_tokens,
            $research->llm_output_tokens, $research->estimated_cost_usd, $research->started_at, $research->completed_at,
            $research->created_at->toImmutable(), $research->updated_at->toImmutable(),
            $research->sources->map(fn ($source) => ResearchSourceData::fromModel($source))->all(),
            $research->facts->map(fn ($fact) => ResearchFactData::fromModel($fact))->all(),
        );
    }
}
