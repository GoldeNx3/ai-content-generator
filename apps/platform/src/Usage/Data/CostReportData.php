<?php

namespace Modules\Usage\Data;

use Spatie\LaravelData\Data;

final class CostReportData extends Data
{
    public function __construct(
        public string $month,
        public string $total_usd,
        public int $unknown_cost_calls,
        public array $by_kind,
        public array $by_stage,
        public array $articles,
    ) {}
}
