<?php

namespace Modules\Workspaces\Http\Controllers;

use Modules\Workspaces\Data\EditorialProfileData;
use Modules\Workspaces\Services\CurrentWorkspace;
use Modules\Workspaces\Services\EditorialProfileService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowEditorialProfileController
{
    public function __construct(private readonly EditorialProfileService $profiles, private readonly CurrentWorkspace $workspace) {}

    #[Get('workspace/editorial')]
    public function __invoke(): EditorialProfileData
    {
        return $this->profiles->show($this->workspace->id());
    }
}
