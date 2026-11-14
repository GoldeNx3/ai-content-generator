<?php

namespace Modules\Workspaces\Commands;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Models\Workspace;

final class RecordAutomationRunCommand
{
    public function execute(int $workspaceId, CarbonImmutable $startedAt, ?array $result): void
    {
        Workspace::query()->whereKey($workspaceId)->first()?->forceFill([
            'last_auto_run_at' => $startedAt,
            'last_auto_run_result' => $result,
        ])->save();
    }
}
