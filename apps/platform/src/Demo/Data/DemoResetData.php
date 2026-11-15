<?php

namespace Modules\Demo\Data;

use Spatie\LaravelData\Data;

final class DemoResetData extends Data
{
    public function __construct(
        public int $removed,
        public int $created,
    ) {}
}
