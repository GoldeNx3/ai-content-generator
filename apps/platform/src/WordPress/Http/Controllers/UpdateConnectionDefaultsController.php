<?php

namespace Modules\WordPress\Http\Controllers;

use Modules\WordPress\Data\ConnectionData;
use Modules\WordPress\Data\ConnectionDefaultsData;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateConnectionDefaultsController
{
    public function __construct(private readonly ConnectionService $connections, private readonly CurrentWorkspace $workspace) {}

    #[Patch('wordpress/connection')]
    public function __invoke(ConnectionDefaultsData $data): ConnectionData
    {
        return ConnectionData::fromModel($this->connections->updateDefaults($this->workspace->id(), $data->values()));
    }
}
