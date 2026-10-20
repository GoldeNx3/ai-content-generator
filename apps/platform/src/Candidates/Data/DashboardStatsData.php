<?php

namespace Modules\Candidates\Data;

use Spatie\LaravelData\Data;

final class DashboardStatsData extends Data
{
    public function __construct(
        public int $candidates_today,
        public int $new_today,
        public int $approved,
        public int $ignored,
        public ?float $average_score,
    ) {}
}
