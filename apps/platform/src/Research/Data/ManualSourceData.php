<?php

namespace Modules\Research\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Attributes\Validation\Url;
use Spatie\LaravelData\Data;

final class ManualSourceData extends Data
{
    public function __construct(
        #[Required, Url(['http', 'https']), Max(2048)]
        public string $url,
    ) {}
}
