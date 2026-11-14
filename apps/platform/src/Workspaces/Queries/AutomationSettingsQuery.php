<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\Workspace;

final class AutomationSettingsQuery
{
    public function execute(int $workspaceId): Workspace
    {
        return Workspace::query()->findOrFail($workspaceId);
    }
}
