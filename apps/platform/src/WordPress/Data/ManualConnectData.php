<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class ManualConnectData extends Data
{
    public function __construct(
        #[Required, Max(2048)]
        public string $site_url,
        #[Required, Min(1), Max(200)]
        public string $username,
        #[Required, Min(1), Max(200)]
        public string $app_password,
        #[Max(2048)]
        public ?string $api_url = null,
        public bool $confirm_site_change = false,
    ) {}
}
