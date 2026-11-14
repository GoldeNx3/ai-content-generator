<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Data\ConnectionData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware(['auth:sanctum', 'throttle:expensive'])]
final class TestConnectionController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Post('wordpress/connection/test')]
    public function __invoke(): JsonResponse
    {
        return response()->json(ConnectionData::fromModel($this->connections->test($this->workspace->id())));
    }
}
