<?php

namespace Modules\Candidates\Http\Controllers;

use Modules\Candidates\Data\DashboardStatsData;
use Modules\Candidates\Services\CandidateService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class DashboardStatsController
{
    public function __construct(private readonly CandidateService $candidates, private readonly CurrentWorkspace $workspace) {}

    #[Get('stats')]
    public function __invoke(): DashboardStatsData
    {
        return $this->candidates->stats($this->workspace->id());
    }
}
