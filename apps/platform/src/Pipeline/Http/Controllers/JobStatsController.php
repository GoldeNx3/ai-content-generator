<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Pipeline\Services\JobService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class JobStatsController
{
    public function __construct(private readonly JobService $jobs, private readonly CurrentWorkspace $workspace) {}

    #[Get('jobs/stats')]
    public function __invoke(): JsonResponse
    {
        return response()->json($this->jobs->stats($this->workspace->id()));
    }
}
