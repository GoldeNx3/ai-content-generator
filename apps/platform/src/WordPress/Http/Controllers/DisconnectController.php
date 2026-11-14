<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\Response;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Delete;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class DisconnectController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Delete('wordpress/connection')]
    public function __invoke(): Response
    {
        $this->connections->disconnect($this->workspace->id());

        return response()->noContent();
    }
}
