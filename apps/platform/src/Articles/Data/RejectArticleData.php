<?php

namespace Modules\Articles\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class RejectArticleData extends Data
{
    public function __construct(
        #[Max(2000)]
        public ?string $reason = null,
    ) {}
}
