<?php

namespace Modules\Auth\Commands;

use Carbon\CarbonImmutable;
use Modules\Auth\Models\User;

final class RecordLoginCommand
{
    public function execute(int $userId): void
    {
        User::query()->whereKey($userId)->update(['last_login_at' => CarbonImmutable::now()]);
    }
}
