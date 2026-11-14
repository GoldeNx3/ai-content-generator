<?php

namespace Modules\Workspaces\Http\Controllers;

use Modules\Workspaces\Data\AutomationSettingsData;
use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Services\AutomationSettingsService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowAutomationController
{
    public function __construct(private readonly AutomationSettingsService $automation, private readonly CurrentWorkspace $workspace) {}

    #[Get('workspace/automation')]
    public function __invoke(): AutomationSettingsData
    {
        $workspace = $this->workspace->get();

        return $this->automation->show($workspace->id, $workspace->role === WorkspaceRole::Owner);
    }
}
