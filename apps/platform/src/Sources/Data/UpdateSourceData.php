<?php

namespace Modules\Sources\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Attributes\Validation\Url;
use Spatie\LaravelData\Data;
use Spatie\LaravelData\Optional;

final class UpdateSourceData extends Data
{
    public function __construct(
        #[Min(1), Max(200)]
        public string|Optional $name,
        #[Url(['http', 'https']), Max(2048)]
        public string|Optional $url,
        public bool|Optional $active,
    ) {}
}
