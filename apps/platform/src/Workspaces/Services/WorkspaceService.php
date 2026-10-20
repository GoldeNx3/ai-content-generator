<?php

namespace Modules\Workspaces\Services;

use Illuminate\Support\Str;
use Modules\Workspaces\Commands\AddWorkspaceMemberCommand;
use Modules\Workspaces\Commands\CreateWorkspaceCommand;
use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Models\Workspace;

final class WorkspaceService
{
    public function __construct(
        private readonly CreateWorkspaceCommand $createWorkspace,
        private readonly AddWorkspaceMemberCommand $addMember,
    ) {}

    public function createForOwner(int $userId, string $email): Workspace
    {
        $workspace = $this->createWorkspace->execute(Str::before($email, '@') ?: $email);
        $this->addMember->execute($workspace->id, $userId, WorkspaceRole::Owner);

        return $workspace;
    }

    public function join(int $workspaceId, int $userId, WorkspaceRole $role = WorkspaceRole::Owner): void
    {
        $this->addMember->execute($workspaceId, $userId, $role);
    }
}
