<?php

namespace Modules\Articles\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Candidates\Enums\CandidateCategory;
use Modules\Candidates\Models\Candidate;

#[Guarded(['id'])]
class Article extends Model
{
    protected $attributes = [
        'status' => 'draft', 'created_by' => 'generated', 'content_hash' => '', 'auto_fix_iteration' => 0,
        'is_current' => true, 'qa_passed' => false, 'is_edited' => false, 'seo_data' => '{}', 'seo_preview' => '{}', 'seo_origin' => 'article',
        'lead_fact_ids' => '[]', 'validation_warnings' => '[]',
    ];

    protected function casts(): array
    {
        return [
            'status' => ArticleStatus::class,
            'article_type' => CandidateCategory::class,
            'is_current' => 'boolean',
            'qa_passed' => 'boolean',
            'is_edited' => 'boolean',
            'seo_data' => 'array',
            'seo_preview' => 'array',
            'brief' => 'array',
            'sections' => 'array',
            'lead_fact_ids' => 'array',
            'generation_options' => 'array',
            'research_snapshot' => 'array',
            'validation_warnings' => 'array',
            'estimated_cost_usd' => 'decimal:6',
            'brief_cost_usd' => 'decimal:6',
            'writer_cost_usd' => 'decimal:6',
            'approved_at' => 'immutable_datetime',
        ];
    }

    public function candidate(): BelongsTo
    {
        return $this->belongsTo(Candidate::class);
    }

    public function articleFormat(): string
    {
        return ($this->brief['article_format'] ?? null)
            ?: (['guide' => 'guide', 'comparison' => 'comparison', 'news' => 'news'][$this->article_type?->value] ?? 'explainer');
    }
}
