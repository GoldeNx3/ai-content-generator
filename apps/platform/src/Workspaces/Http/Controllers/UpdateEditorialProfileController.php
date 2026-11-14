<?php

namespace Modules\Workspaces\Http\Controllers;

use Modules\Workspaces\Data\EditorialProfileData;
use Modules\Workspaces\Services\CurrentWorkspace;
use Modules\Workspaces\Services\EditorialProfileService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateEditorialProfileController
{
    public function __construct(private readonly EditorialProfileService $profiles, private readonly CurrentWorkspace $workspace) {}

    #[Patch('workspace/editorial')]
    public function __invoke(EditorialProfileData $data): EditorialProfileData
    {
        return $this->profiles->update($this->workspace->id(), $data);
    }
}
