<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class AuthorizeStartData extends Data
{
    public function __construct(
        #[Required, Max(2048)]
        public string $site_url,
        #[Max(2048)]
        public ?string $api_url = null,
    ) {}
}
