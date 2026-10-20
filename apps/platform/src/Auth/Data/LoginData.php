<?php

namespace Modules\Auth\Data;

use Modules\Shared\Casts\NormalizedEmailCast;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Attributes\WithCast;
use Spatie\LaravelData\Data;

final class LoginData extends Data
{
    public function __construct(
        #[Required, Max(320), WithCast(NormalizedEmailCast::class)]
        public string $email,
        #[Required, Max(1024)]
        public string $password,
    ) {}
}
