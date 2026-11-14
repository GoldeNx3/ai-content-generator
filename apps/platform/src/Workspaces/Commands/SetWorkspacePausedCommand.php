<?php

namespace Modules\Workspaces\Commands;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Models\Workspace;

final class SetWorkspacePausedCommand
{
    public function execute(int $workspaceId, ?CarbonImmutable $pausedAt): void
    {
        Workspace::query()->whereKey($workspaceId)->update(['paused_at' => $pausedAt]);
    }
}
