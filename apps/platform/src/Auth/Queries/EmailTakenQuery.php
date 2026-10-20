<?php

namespace Modules\Auth\Queries;

use Modules\Auth\Models\User;

final class EmailTakenQuery
{
    public function execute(string $email): bool
    {
        return User::query()->where('email', $email)->exists();
    }
}
