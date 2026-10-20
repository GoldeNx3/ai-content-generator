<?php

namespace Modules\Shared\Data;

use Spatie\LaravelData\Data;

final class PageData extends Data
{
    public function __construct(
        public array $items,
        public int $total,
        public int $page,
        public int $page_size,
    ) {}
}
