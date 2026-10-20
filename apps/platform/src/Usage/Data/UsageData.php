<?php

namespace Modules\Usage\Data;

use Carbon\CarbonImmutable;
use Spatie\LaravelData\Data;

final class UsageData extends Data
{
    public function __construct(
        public CarbonImmutable $period_start,
        public string $spent_usd,
        public ?string $budget_usd,
        public ?string $remaining_usd,
        public bool $exceeded,
        public int $unknown_cost_calls,
    ) {}
}
