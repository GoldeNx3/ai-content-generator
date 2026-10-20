<?php

namespace Modules\Workspaces\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Modules\Auth\Models\User;

#[Fillable(['name', 'monthly_budget_usd'])]
class Workspace extends Model
{
    protected function casts(): array
    {
        return ['monthly_budget_usd' => 'decimal:2'];
    }

    public function members(): BelongsToMany
    {
        return $this->belongsToMany(User::class, 'workspace_members')->withPivot('role')->withTimestamps();
    }
}
