<?php

namespace Modules\Auth\Commands;

use Modules\Auth\Models\User;

final class SetUserActiveCommand
{
    public function execute(string $email, bool $active): bool
    {
        return User::query()->where('email', $email)->update(['is_active' => $active]) > 0;
    }
}
