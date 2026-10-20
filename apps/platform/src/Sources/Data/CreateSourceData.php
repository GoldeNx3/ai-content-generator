<?php

namespace Modules\Sources\Data;

use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Attributes\Validation\Url;
use Spatie\LaravelData\Data;

final class CreateSourceData extends Data
{
    public function __construct(
        #[Required, Min(1), Max(200)]
        public string $name,
        #[Required, Url(['http', 'https']), Max(2048)]
        public string $url,
        #[In(['rss'])]
        public string $type = 'rss',
        public bool $active = true,
    ) {}
}
