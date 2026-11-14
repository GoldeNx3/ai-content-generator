<?php

namespace Modules\Workspaces\Http\Controllers;

use Modules\Workspaces\Data\AutomationSettingsData;
use Modules\Workspaces\Data\UpdateAutomationData;
use Modules\Workspaces\Services\AutomationSettingsService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateAutomationController
{
    public function __construct(private readonly AutomationSettingsService $automation, private readonly CurrentWorkspace $workspace) {}

    #[Patch('workspace/automation')]
    public function __invoke(UpdateAutomationData $data): AutomationSettingsData
    {
        $this->workspace->requireOwner();

        return $this->automation->update($this->workspace->id(), $data);
    }
}
