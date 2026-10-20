<?php

namespace Modules\Workspaces\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;
use Modules\Workspaces\Enums\WorkspaceRole;

#[Table('workspace_members', incrementing: false)]
#[Fillable(['workspace_id', 'user_id', 'role'])]
class WorkspaceMember extends Model
{
    protected function casts(): array
    {
        return ['role' => WorkspaceRole::class];
    }
}
