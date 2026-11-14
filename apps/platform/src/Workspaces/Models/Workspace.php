<?php

namespace Modules\Workspaces\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Modules\Auth\Models\User;

#[Fillable([
    'name', 'monthly_budget_usd', 'auto_fetch_enabled', 'auto_fetch_interval_minutes', 'auto_classify_enabled',
    'auto_classify_batch_limit', 'last_auto_run_at', 'last_auto_run_result', 'paused_at', 'editorial_profile',
])]
class Workspace extends Model
{
    protected function casts(): array
    {
        return [
            'monthly_budget_usd' => 'decimal:2',
            'auto_fetch_enabled' => 'boolean',
            'auto_fetch_interval_minutes' => 'integer',
            'auto_classify_enabled' => 'boolean',
            'auto_classify_batch_limit' => 'integer',
            'last_auto_run_at' => 'immutable_datetime',
            'last_auto_run_result' => 'array',
            'paused_at' => 'immutable_datetime',
            'editorial_profile' => 'array',
        ];
    }

    public function members(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'workspace_members')->withPivot('role')->withTimestamps();
    }
}
