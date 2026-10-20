<?php

namespace Modules\Research\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Modules\Candidates\Models\Candidate;
use Modules\Research\Enums\ResearchStatus;

#[Table('researches')]
#[Fillable([
    'candidate_id', 'job_id', 'status', 'summary', 'why_it_matters', 'suggested_angle', 'search_queries',
    'uncertainties', 'conflicts', 'error', 'llm_model', 'llm_input_tokens', 'llm_output_tokens',
    'estimated_cost_usd', 'started_at', 'completed_at',
])]
class Research extends Model
{
    protected $attributes = [
        'status' => 'pending', 'search_queries' => '[]', 'uncertainties' => '[]', 'conflicts' => '[]',
        'llm_input_tokens' => 0, 'llm_output_tokens' => 0,
    ];

    protected function casts(): array
    {
        return [
            'status' => ResearchStatus::class,
            'search_queries' => 'array',
            'uncertainties' => 'array',
            'conflicts' => 'array',
            'estimated_cost_usd' => 'decimal:6',
            'started_at' => 'immutable_datetime',
            'completed_at' => 'immutable_datetime',
        ];
    }

    public function candidate(): BelongsTo
    {
        return $this->belongsTo(Candidate::class);
    }

    public function sources(): HasMany
    {
        return $this->hasMany(ResearchSource::class)->orderBy('id');
    }

    public function facts(): HasMany
    {
        return $this->hasMany(ResearchFact::class)->orderBy('id');
    }
}
