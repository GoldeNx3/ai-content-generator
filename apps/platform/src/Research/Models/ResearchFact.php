<?php

namespace Modules\Research\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

#[Fillable(['research_id', 'claim', 'importance', 'confidence', 'basis'])]
class ResearchFact extends Model
{
    public function sources(): BelongsToMany
    {
        return $this->belongsToMany(ResearchSource::class, 'research_fact_sources', 'fact_id', 'source_id')->orderBy('research_sources.id');
    }
}
