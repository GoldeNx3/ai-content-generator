<?php

namespace Modules\Classification\Queries;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Models\Workspace;

final class DueAutomationWorkspacesQuery
{
    public function execute(CarbonImmutable $now): array
    {
        return Workspace::query()
            ->where('auto_fetch_enabled', true)
            ->whereNull('paused_at')
            ->where(fn ($query) => $query->whereNull('last_auto_run_at')
                ->orWhereRaw('last_auto_run_at <= ?::timestamp - make_interval(mins => auto_fetch_interval_minutes)', [$now->toDateTimeString()]))
            ->orderBy('id')
            ->pluck('id')
            ->all();
    }
}
