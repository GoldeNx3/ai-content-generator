<?php

namespace Modules\Usage\Data;

use Spatie\LaravelData\Attributes\Validation\Regex;
use Spatie\LaravelData\Data;

final class CostReportFilterData extends Data
{
    public function __construct(
        #[Regex('/^\d{4}-(0[1-9]|1[0-2])$/')]
        public ?string $month = null,
    ) {}
}
