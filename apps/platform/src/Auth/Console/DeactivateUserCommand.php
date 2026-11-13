<?php

namespace Modules\Auth\Console;

use Illuminate\Console\Command;
use Modules\Auth\Commands\SetUserActiveCommand;

final class DeactivateUserCommand extends Command
{
    protected $signature = 'users:deactivate {email}';

    protected $description = 'Blokuje konto: odrzuca logowanie i unieważnia aktywne sesje';

    public function handle(SetUserActiveCommand $setActive): int
    {
        $email = mb_strtolower(trim((string) $this->argument('email')));
        if (! $setActive->execute($email, false)) {
            $this->error("Brak konta {$email}");

            return self::FAILURE;
        }
        $this->info("Konto {$email} zablokowane");

        return self::SUCCESS;
    }
}
