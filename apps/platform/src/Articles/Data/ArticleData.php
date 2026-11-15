<?php

namespace Modules\Articles\Data;

use Carbon\CarbonImmutable;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Candidates\Enums\CandidateCategory;
use Spatie\LaravelData\Data;

final class ArticleData extends Data
{
    public function __construct(
        public int $id,
        public int $candidate_id,
        public int $version,
        public bool $is_current,
        public ArticleStatus $status,
        public string $title,
        public CandidateCategory $article_type,
        public string $article_format,
        public int $word_count,
        public ?int $parent_version_id,
        public string $created_by,
        public ?string $creation_reason,
        public string $content_hash,
        public int $auto_fix_iterations_remaining,
        public int $auto_fix_iteration,
        public ?CarbonImmutable $approved_at,
        public ?string $approved_by,
        public ?string $rejection_reason,
        public ?int $qa_score,
        public string $qa_status,
        public bool $qa_passed,
        public bool $is_edited,
        public ?string $estimated_cost_usd,
        public ?string $llm_model,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
        public string $seo_title,
        public array $seo_data,
        public array $seo_preview,
        public string $seo_origin,
        public ?int $research_id,
        public string $slug,
        public string $lead,
        public string $content,
        public string $generated_content,
        public string $meta_title,
        public string $meta_description,
        public ?string $angle,
        public array $brief,
        public array $sections,
        public array $lead_fact_ids,
        public array $generation_options,
        public array $research_snapshot,
        public array $validation_warnings,
        public int $sections_count,
        public int $facts_used_count,
        public int $facts_available_count,
        public int $source_count,
        public int $llm_input_tokens,
        public int $llm_output_tokens,
        public ?string $brief_llm_model,
        public int $brief_input_tokens,
        public int $brief_output_tokens,
        public ?string $brief_cost_usd,
        public int $writer_input_tokens,
        public int $writer_output_tokens,
        public ?string $writer_cost_usd,
        public ?array $refresh_of = null,
    ) {}

    public static function fromModel(Article $article, ArticleQaState $state): self
    {
        return new self(...ArticleSummaryData::attributes($article, $state), ...[
            'seo_title' => $article->meta_title, 'seo_data' => $article->seo_data ?? [], 'seo_preview' => $article->seo_preview ?? [],
            'seo_origin' => $article->seo_origin, 'research_id' => $article->research_id, 'slug' => $article->slug,
            'lead' => $article->lead, 'content' => $article->content, 'generated_content' => $article->generated_content,
            'meta_title' => $article->meta_title, 'meta_description' => $article->meta_description, 'angle' => $article->angle,
            'brief' => $article->brief ?? [], 'sections' => $article->sections ?? [], 'lead_fact_ids' => $article->lead_fact_ids ?? [],
            'generation_options' => $article->generation_options ?? [], 'research_snapshot' => $article->research_snapshot ?? [],
            'validation_warnings' => $article->validation_warnings ?? [], 'sections_count' => $article->sections_count,
            'facts_used_count' => $article->facts_used_count, 'facts_available_count' => $article->facts_available_count,
            'source_count' => $article->source_count, 'llm_input_tokens' => $article->llm_input_tokens,
            'llm_output_tokens' => $article->llm_output_tokens, 'brief_llm_model' => $article->brief_llm_model,
            'brief_input_tokens' => $article->brief_input_tokens, 'brief_output_tokens' => $article->brief_output_tokens,
            'brief_cost_usd' => $article->brief_cost_usd, 'writer_input_tokens' => $article->writer_input_tokens,
            'writer_output_tokens' => $article->writer_output_tokens, 'writer_cost_usd' => $article->writer_cost_usd,
        ]);
    }
}
