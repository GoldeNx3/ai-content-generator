<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\Workspace;

final class WorkspacePausedQuery
{
    public function execute(int $workspaceId): bool
    {
        return Workspace::query()->whereKey($workspaceId)->whereNotNull('paused_at')->exists();
    }
}
