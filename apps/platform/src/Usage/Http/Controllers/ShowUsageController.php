<?php

namespace Modules\Usage\Http\Controllers;

use Modules\Usage\Data\UsageData;
use Modules\Usage\Services\BudgetService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowUsageController
{
    public function __construct(private readonly BudgetService $budget, private readonly CurrentWorkspace $workspace) {}

    #[Get('usage')]
    public function __invoke(): UsageData
    {
        return $this->budget->usage($this->workspace->id());
    }
}
