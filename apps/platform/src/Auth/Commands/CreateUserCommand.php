<?php

namespace Modules\Auth\Commands;

use Modules\Auth\Models\User;

final class CreateUserCommand
{
    public function execute(string $email, string $password): User
    {
        return User::query()->create(['email' => $email, 'password' => $password]);
    }
}
