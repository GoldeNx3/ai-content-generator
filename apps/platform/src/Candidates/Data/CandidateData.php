<?php

namespace Modules\Candidates\Data;

use Carbon\CarbonImmutable;
use Modules\Candidates\Enums\CandidateCategory;
use Modules\Candidates\Enums\CandidateStatus;
use Modules\Candidates\Enums\WorkflowStatus;
use Modules\Candidates\Models\Candidate;
use Spatie\LaravelData\Data;

final class CandidateData extends Data
{
    public function __construct(
        public int $id,
        public int $source_id,
        public string $source_name,
        public bool $is_demo,
        public string $external_url,
        public string $title,
        public ?string $summary,
        public ?CarbonImmutable $original_published_at,
        public CandidateStatus $status,
        public ?WorkflowStatus $workflow_status,
        public ?int $relevance_score,
        public ?int $freshness_score,
        public ?int $search_potential_score,
        public ?int $commercial_potential_score,
        public ?int $total_score,
        public ?CandidateCategory $category,
        public ?string $llm_reason,
        public ?string $llm_model,
        public ?int $llm_input_tokens,
        public ?int $llm_output_tokens,
        public ?string $estimated_cost_usd,
        public ?CarbonImmutable $classified_at,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
        public int $group_size = 1,
        public ?int $topic_group_id = null,
        public ?float $duplicate_similarity = null,
        public ?array $topic_group = null,
        public ?string $editor_take = null,
        public ?array $covered_by = null,
    ) {}

    public static function fromModel(Candidate $candidate): self
    {
        return new self(
            $candidate->id, $candidate->source_id, $candidate->source_name ?? $candidate->source->name, $candidate->isDemo(),
            $candidate->external_url, $candidate->title, $candidate->summary, $candidate->original_published_at,
            $candidate->status, WorkflowStatus::tryFrom((string) $candidate->workflow_status),
            $candidate->relevance_score, $candidate->freshness_score, $candidate->search_potential_score,
            $candidate->commercial_potential_score, $candidate->total_score, $candidate->category, $candidate->llm_reason,
            $candidate->llm_model, $candidate->llm_input_tokens, $candidate->llm_output_tokens, $candidate->estimated_cost_usd,
            $candidate->classified_at, $candidate->created_at->toImmutable(), $candidate->updated_at->toImmutable(),
            (int) ($candidate->group_size ?? 1), $candidate->topic_group_id, $candidate->duplicate_similarity, null, $candidate->editor_take, $candidate->covered_by,
        );
    }
}
