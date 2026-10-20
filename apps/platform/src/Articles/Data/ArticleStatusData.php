<?php

namespace Modules\Articles\Data;

use Modules\Articles\Enums\ArticleStatus;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class ArticleStatusData extends Data
{
    public function __construct(
        #[Required]
        public ArticleStatus $status,
    ) {}
}
