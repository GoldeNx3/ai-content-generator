<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Data\AuthorizeStartData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware(['auth:sanctum', 'throttle:expensive'])]
final class StartAuthorizationController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Post('wordpress/connection/authorize')]
    public function __invoke(AuthorizeStartData $data): JsonResponse
    {
        $url = $this->connections->startAuthorization($this->workspace->id(), (int) auth()->id(), $data->site_url, $data->api_url);

        return response()->json(['authorize_url' => $url]);
    }
}
