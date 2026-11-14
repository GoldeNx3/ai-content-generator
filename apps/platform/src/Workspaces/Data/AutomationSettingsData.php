<?php

namespace Modules\Workspaces\Data;

use Carbon\CarbonImmutable;
use Spatie\LaravelData\Data;

final class AutomationSettingsData extends Data
{
    public function __construct(
        public bool $auto_fetch_enabled,
        public int $auto_fetch_interval_minutes,
        public bool $auto_classify_enabled,
        public int $auto_classify_batch_limit,
        public ?CarbonImmutable $last_auto_run_at,
        public ?array $last_auto_run_result,
        public ?CarbonImmutable $next_auto_run_at,
        public ?CarbonImmutable $paused_at,
        public bool $automation_enabled_globally,
        public bool $can_edit,
    ) {}
}
