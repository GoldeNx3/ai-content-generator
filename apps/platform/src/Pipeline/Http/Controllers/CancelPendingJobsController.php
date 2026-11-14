<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Pipeline\Services\JobCancellationService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class CancelPendingJobsController
{
    public function __construct(private readonly JobCancellationService $cancellation, private readonly CurrentWorkspace $workspace) {}

    #[Post('jobs/cancel-pending')]
    public function __invoke(Request $request): JsonResponse
    {
        return response()->json(['cancelled' => $this->cancellation->cancelPending($this->workspace->id(), $request->user()?->id)]);
    }
}
