<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Data\WorkspaceData;
use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Models\Workspace;

final class UserMembershipQuery
{
    public function execute(int $userId, ?int $workspaceId = null): ?WorkspaceData
    {
        $row = Workspace::query()
            ->join('workspace_members', 'workspace_members.workspace_id', '=', 'workspaces.id')
            ->where('workspace_members.user_id', $userId)
            ->when($workspaceId !== null, fn ($query) => $query->where('workspaces.id', $workspaceId))
            ->orderBy('workspace_members.created_at')
            ->orderBy('workspaces.id')
            ->first(['workspaces.id', 'workspaces.name', 'workspace_members.role']);

        return $row === null ? null : new WorkspaceData($row->id, $row->name, WorkspaceRole::from($row->role));
    }
}
