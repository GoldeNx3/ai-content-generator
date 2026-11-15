<?php

namespace Modules\Auth\Data;

use Spatie\LaravelData\Attributes\Validation\Confirmed;
use Spatie\LaravelData\Attributes\Validation\Different;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class ChangePasswordData extends Data
{
    public function __construct(
        #[Required, Max(1024)]
        public string $current_password,
        #[Required, Min(10), Max(1024), Confirmed, Different('current_password')]
        public string $password,
    ) {}
}
