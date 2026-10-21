<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Data\ConnectionData;
use Modules\WordPress\Data\ManualConnectData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ConnectManuallyController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Post('wordpress/connection')]
    public function __invoke(ManualConnectData $data): JsonResponse
    {
        $this->workspace->requireOwner();
        $connection = $this->connections->connect($this->workspace->id(), $data->site_url, $data->api_url, $data->username, $data->app_password, $data->confirm_site_change);

        return response()->json(ConnectionData::fromModel($connection));
    }
}
