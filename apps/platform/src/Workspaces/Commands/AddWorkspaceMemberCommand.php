<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Models\WorkspaceMember;

final class AddWorkspaceMemberCommand
{
    public function execute(int $workspaceId, int $userId, WorkspaceRole $role): void
    {
        WorkspaceMember::query()->create(['workspace_id' => $workspaceId, 'user_id' => $userId, 'role' => $role]);
    }
}
