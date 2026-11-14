<?php

namespace Modules\Usage\Services;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Usage\Data\UsageData;
use Modules\Usage\Queries\WorkspaceBudgetQuery;
use Modules\Usage\Queries\WorkspaceSpendQuery;

final class BudgetService
{
    public function __construct(
        private readonly WorkspaceSpendQuery $spend,
        private readonly WorkspaceBudgetQuery $budget,
    ) {}

    public function usage(int $workspaceId): UsageData
    {
        $start = CarbonImmutable::now('UTC')->startOfMonth();
        [$spent, $unknown] = $this->spend->execute($workspaceId, $start);
        $budget = $this->budget->execute($workspaceId);
        $remaining = $budget === null ? null : number_format(max(0.0, (float) $budget - (float) $spent), 6, '.', '');

        return new UsageData($start, $spent, $budget, $remaining, $budget !== null && (float) $spent >= (float) $budget, $unknown);
    }

    public function ensureAvailable(int $workspaceId): void
    {
        if ($this->isExceeded($workspaceId)) {
            throw new JobInputException('budget_exceeded', 402);
        }
    }

    public function isExceeded(int $workspaceId): bool
    {
        return $this->budget->execute($workspaceId) !== null && $this->usage($workspaceId)->exceeded;
    }
}
