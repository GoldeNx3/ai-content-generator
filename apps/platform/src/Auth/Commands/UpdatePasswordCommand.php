<?php

namespace Modules\Auth\Commands;

use Modules\Auth\Models\User;

final class UpdatePasswordCommand
{
    public function execute(User $user, string $password): void
    {
        $user->forceFill(['password' => $password])->save();
    }
}
