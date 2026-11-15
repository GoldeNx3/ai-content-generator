<?php

namespace Modules\Usage\Http\Controllers;

use Modules\Usage\Data\CostReportData;
use Modules\Usage\Data\CostReportFilterData;
use Modules\Usage\Services\CostReportService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowCostReportController
{
    public function __construct(private readonly CostReportService $reports, private readonly CurrentWorkspace $workspace) {}

    #[Get('usage/report')]
    public function __invoke(CostReportFilterData $filter): CostReportData
    {
        return $this->reports->month($this->workspace->id(), $filter->month);
    }
}
