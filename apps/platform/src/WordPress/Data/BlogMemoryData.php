<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Data;

final class BlogMemoryData extends Data
{
    public function __construct(
        public int $count,
        public ?string $synced_at,
    ) {}
}
