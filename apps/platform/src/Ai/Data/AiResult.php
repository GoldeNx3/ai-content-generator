<?php

namespace Modules\Ai\Data;

use Spatie\LaravelData\Data;

final class AiResult extends Data
{
    public function __construct(
        public array $result,
        public array $calls,
    ) {}
}
