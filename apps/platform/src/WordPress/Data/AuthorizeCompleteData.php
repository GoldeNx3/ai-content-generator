<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class AuthorizeCompleteData extends Data
{
    public function __construct(
        #[Required, Min(10), Max(200)]
        public string $state,
        #[Required, Min(1), Max(200)]
        public string $user_login,
        #[Required, Min(1), Max(200)]
        public string $password,
        public bool $confirm_site_change = false,
    ) {}
}
