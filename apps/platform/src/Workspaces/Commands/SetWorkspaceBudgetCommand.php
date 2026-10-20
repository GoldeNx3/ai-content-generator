<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\Workspace;

final class SetWorkspaceBudgetCommand
{
    public function execute(int $workspaceId, ?string $budgetUsd): Workspace
    {
        $workspace = Workspace::query()->findOrFail($workspaceId);
        $workspace->update(['monthly_budget_usd' => $budgetUsd]);

        return $workspace;
    }
}
