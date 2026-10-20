<?php

namespace Modules\Pipeline\Http\Controllers;

use Modules\Pipeline\Data\QueueFiltersData;
use Modules\Pipeline\Services\JobService;
use Modules\Shared\Data\PageData;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ListJobsController
{
    public function __construct(private readonly JobService $jobs, private readonly CurrentWorkspace $workspace) {}

    #[Get('jobs')]
    public function __invoke(QueueFiltersData $filters): PageData
    {
        return $this->jobs->list($this->workspace->id(), $filters);
    }
}
