<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Data\ConnectionData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowConnectionController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Get('wordpress/connection')]
    public function __invoke(): JsonResponse
    {
        $connection = $this->connections->find($this->workspace->id());

        return response()->json($connection === null ? null : ConnectionData::fromModel($connection));
    }
}
