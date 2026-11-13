<?php

namespace Modules\Auth\Console;

use Illuminate\Console\Command;
use Modules\Auth\Commands\SetUserActiveCommand;

final class ActivateUserCommand extends Command
{
    protected $signature = 'users:activate {email}';

    protected $description = 'Odblokowuje konto (logowanie znów możliwe)';

    public function handle(SetUserActiveCommand $setActive): int
    {
        $email = mb_strtolower(trim((string) $this->argument('email')));
        if (! $setActive->execute($email, true)) {
            $this->error("Brak konta {$email}");

            return self::FAILURE;
        }
        $this->info("Konto {$email} aktywne");

        return self::SUCCESS;
    }
}
