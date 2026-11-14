<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Data\WorkspaceData;
use Modules\Workspaces\Models\Workspace;

final class UserMembershipQuery
{
    public function execute(int $userId): ?WorkspaceData
    {
        $row = Workspace::query()
            ->join('workspace_members', 'workspace_members.workspace_id', '=', 'workspaces.id')
            ->where('workspace_members.user_id', $userId)
            ->first(['workspaces.id', 'workspaces.name']);

        return $row === null ? null : new WorkspaceData($row->id, $row->name);
    }
}
