<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\Workspace;

final class UpdateAutomationCommand
{
    public function execute(int $workspaceId, array $changes): void
    {
        if ($changes !== []) {
            Workspace::query()->whereKey($workspaceId)->update($changes);
        }
    }
}
