<?php

namespace Modules\Sources\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Modules\Candidates\Models\Candidate;

#[Fillable(['workspace_id', 'name', 'type', 'url', 'active', 'last_fetched_at'])]
class Source extends Model
{
    protected function casts(): array
    {
        return ['active' => 'boolean', 'last_fetched_at' => 'immutable_datetime'];
    }

    public function candidates(): HasMany
    {
        return $this->hasMany(Candidate::class);
    }
}
