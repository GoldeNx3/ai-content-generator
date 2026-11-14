<?php

namespace Modules\Workspaces\Services;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Commands\UpdateAutomationCommand;
use Modules\Workspaces\Data\AutomationSettingsData;
use Modules\Workspaces\Data\UpdateAutomationData;
use Modules\Workspaces\Models\Workspace;
use Modules\Workspaces\Queries\AutomationSettingsQuery;

final class AutomationSettingsService
{
    public function __construct(
        private readonly AutomationSettingsQuery $settings,
        private readonly UpdateAutomationCommand $updateSettings,
    ) {}

    public function show(int $workspaceId, bool $canEdit): AutomationSettingsData
    {
        $workspace = $this->settings->execute($workspaceId);
        $global = (bool) config('content.automation.enabled');

        return new AutomationSettingsData(
            $workspace->auto_fetch_enabled,
            $workspace->auto_fetch_interval_minutes,
            $workspace->auto_classify_enabled,
            $workspace->auto_classify_batch_limit,
            $workspace->last_auto_run_at,
            $workspace->last_auto_run_result,
            $this->nextRun($workspace, $global),
            $workspace->paused_at,
            $global,
            $canEdit,
        );
    }

    public function update(int $workspaceId, UpdateAutomationData $data): AutomationSettingsData
    {
        $this->updateSettings->execute($workspaceId, $data->changes());

        return $this->show($workspaceId, true);
    }

    private function nextRun(Workspace $workspace, bool $global): ?CarbonImmutable
    {
        if (! $global || ! $workspace->auto_fetch_enabled || $workspace->paused_at !== null) {
            return null;
        }
        $now = CarbonImmutable::now();
        if ($workspace->last_auto_run_at === null) {
            return $now;
        }
        $next = $workspace->last_auto_run_at->addMinutes($workspace->auto_fetch_interval_minutes);

        return $next->lessThan($now) ? $now : $next;
    }
}
