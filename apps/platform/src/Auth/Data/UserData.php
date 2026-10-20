<?php

namespace Modules\Auth\Data;

use Spatie\LaravelData\Data;

final class UserData extends Data
{
    public function __construct(
        public int $id,
        public string $email,
    ) {}
}
