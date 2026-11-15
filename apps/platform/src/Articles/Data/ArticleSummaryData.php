<?php

namespace Modules\Articles\Data;

use Carbon\CarbonImmutable;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Candidates\Enums\CandidateCategory;
use Spatie\LaravelData\Data;

final class ArticleSummaryData extends Data
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
        public ?array $refresh_of = null,
    ) {}

    public static function fromModel(Article $article, ArticleQaState $state): self
    {
        return new self(...self::attributes($article, $state));
    }

    public static function attributes(Article $article, ArticleQaState $state): array
    {
        return [
            'id' => $article->id, 'candidate_id' => $article->candidate_id, 'version' => $article->version,
            'is_current' => $article->is_current, 'status' => $article->status, 'title' => $article->title,
            'article_type' => $article->article_type, 'article_format' => $article->articleFormat(),
            'word_count' => $article->word_count, 'parent_version_id' => $article->parent_version_id,
            'created_by' => $article->created_by, 'creation_reason' => $article->creation_reason,
            'content_hash' => $article->content_hash, 'auto_fix_iterations_remaining' => $state->autoFixIterationsRemaining,
            'auto_fix_iteration' => $article->auto_fix_iteration, 'approved_at' => $article->approved_at,
            'approved_by' => $article->approved_by, 'rejection_reason' => $article->rejection_reason,
            'qa_score' => $state->qaScore, 'qa_status' => $state->qaStatus, 'qa_passed' => $article->qa_passed,
            'is_edited' => $article->is_edited, 'estimated_cost_usd' => $article->estimated_cost_usd,
            'llm_model' => $article->llm_model, 'created_at' => $article->created_at->toImmutable(),
            'updated_at' => $article->updated_at->toImmutable(), 'refresh_of' => $article->refresh_of,
        ];
    }
}
