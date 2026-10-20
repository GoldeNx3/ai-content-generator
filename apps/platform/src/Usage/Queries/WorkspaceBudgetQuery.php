<?php

namespace Modules\Usage\Queries;

use Modules\Workspaces\Models\Workspace;

final class WorkspaceBudgetQuery
{
    public function execute(int $workspaceId): ?string
    {
        $own = Workspace::query()->whereKey($workspaceId)->value('monthly_budget_usd');
        if ($own !== null) {
            return number_format((float) $own, 2, '.', '');
        }
        $default = config('content.default_monthly_budget_usd');

        return $default === null ? null : number_format((float) $default, 2, '.', '');
    }
}
