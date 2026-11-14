<?php

namespace Modules\Candidates\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Modules\Candidates\Enums\CandidateCategory;
use Modules\Candidates\Enums\CandidateStatus;
use Modules\Research\Models\Research;
use Modules\Sources\Models\Source;

#[Fillable([
    'workspace_id', 'source_id', 'external_url', 'title', 'summary', 'original_published_at', 'status',
    'relevance_score', 'freshness_score', 'search_potential_score', 'commercial_potential_score', 'total_score',
    'category', 'llm_reason', 'llm_model', 'llm_input_tokens', 'llm_output_tokens', 'estimated_cost_usd',
    'classified_at', 'classification_job_id', 'topic_group_id', 'duplicate_similarity', 'url_key',
])]
class Candidate extends Model
{
    public const DEMO_PREFIX = 'https://demo.content-engine.invalid/';

    protected $attributes = ['status' => 'pending'];

    protected function casts(): array
    {
        return [
            'status' => CandidateStatus::class,
            'category' => CandidateCategory::class,
            'original_published_at' => 'immutable_datetime',
            'classified_at' => 'immutable_datetime',
            'estimated_cost_usd' => 'decimal:6',
            'topic_group_id' => 'integer',
            'duplicate_similarity' => 'float',
        ];
    }

    public function source(): BelongsTo
    {
        return $this->belongsTo(Source::class);
    }

    public function research(): HasOne
    {
        return $this->hasOne(Research::class);
    }

    public function isDemo(): bool
    {
        return str_starts_with($this->external_url, self::DEMO_PREFIX);
    }
}
