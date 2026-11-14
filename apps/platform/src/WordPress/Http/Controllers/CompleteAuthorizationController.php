<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Data\AuthorizeCompleteData;
use Modules\WordPress\Data\ConnectionData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class CompleteAuthorizationController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Post('wordpress/connection/authorize/complete')]
    public function __invoke(AuthorizeCompleteData $data): JsonResponse
    {
        $connection = $this->connections->completeAuthorization($this->workspace->id(), (int) auth()->id(), $data->state,
            $data->user_login, $data->password, $data->confirm_site_change);

        return response()->json(ConnectionData::fromModel($connection));
    }
}
