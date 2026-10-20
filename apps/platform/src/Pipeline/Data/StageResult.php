<?php

namespace Modules\Pipeline\Data;

final readonly class StageResult
{
    public function __construct(
        public ?string $type = null,
        public ?int $id = null,
    ) {}
}
