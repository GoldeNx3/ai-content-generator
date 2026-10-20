<?php

namespace Modules\Auth\Console;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Validator;
use Modules\Auth\Services\AuthService;
use Modules\Shared\Exceptions\ApiException;

final class CreateUserCommand extends Command
{
    protected $signature = 'users:create {email} {--workspace= : Dołącz jako owner istniejącego workspace\'u}';

    protected $description = 'Zakłada konto (nowy workspace albo dołączenie do istniejącego)';

    public function handle(AuthService $auth): int
    {
        $email = mb_strtolower(trim((string) $this->argument('email')));
        $password = (string) $this->secret('Hasło (min. 10 znaków)');
        $validator = Validator::make(['email' => $email, 'password' => $password], [
            'email' => ['required', 'email', 'max:320'],
            'password' => ['required', 'min:10', 'max:1024'],
        ]);
        if ($validator->fails()) {
            $this->error($validator->errors()->first());

            return self::FAILURE;
        }
        $workspace = $this->option('workspace');
        try {
            $user = $auth->createAccount($email, $password, $workspace === null ? null : (int) $workspace);
        } catch (ApiException $exception) {
            $this->error($exception->errorCode);

            return self::FAILURE;
        }
        $this->info("Utworzono konto {$user->email}");

        return self::SUCCESS;
    }
}
