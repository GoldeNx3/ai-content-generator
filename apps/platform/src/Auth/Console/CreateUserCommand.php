<?php

namespace Modules\Auth\Console;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Validator;
use Modules\Auth\Services\AuthService;
use Modules\Shared\Exceptions\ApiException;

final class CreateUserCommand extends Command
{
    protected $signature = 'users:create {email}';

    protected $description = 'Zakłada konto z własnym, odrębnym workspace\'em (jedno konto = jeden tenant)';

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
        try {
            $user = $auth->createAccount($email, $password);
        } catch (ApiException $exception) {
            $this->error($exception->errorCode);

            return self::FAILURE;
        }
        $this->info("Utworzono konto {$user->email}");

        return self::SUCCESS;
    }
}
