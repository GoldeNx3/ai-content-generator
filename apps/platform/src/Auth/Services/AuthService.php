<?php

namespace Modules\Auth\Services;

use Illuminate\Contracts\Auth\StatefulGuard;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\RateLimiter;
use Modules\Auth\Commands\CreateUserCommand;
use Modules\Auth\Commands\RecordLoginCommand;
use Modules\Auth\Data\LoginData;
use Modules\Auth\Data\MeData;
use Modules\Auth\Data\RegisterData;
use Modules\Auth\Data\UserData;
use Modules\Auth\Models\User;
use Modules\Auth\Queries\EmailTakenQuery;
use Modules\Shared\Exceptions\ApiException;
use Modules\Workspaces\Services\CurrentWorkspace;
use Modules\Workspaces\Services\WorkspaceService;

final class AuthService
{
    public function __construct(
        private readonly CreateUserCommand $createUser,
        private readonly RecordLoginCommand $recordLogin,
        private readonly EmailTakenQuery $emailTaken,
        private readonly WorkspaceService $workspaces,
        private readonly CurrentWorkspace $currentWorkspace,
    ) {}

    public function register(RegisterData $data, Request $request): MeData
    {
        if (! config('content.allow_registration')) {
            throw new ApiException('registration_disabled', 403);
        }
        $limit = config('content.auth.max_registrations_per_ip');
        $key = 'register:ip:'.$request->ip();
        if (RateLimiter::tooManyAttempts($key, $limit)) {
            throw new ApiException('too_many_registrations', 429);
        }
        RateLimiter::hit($key, config('content.auth.registration_window_minutes') * 60);

        $user = $this->createAccount($data->email, $data->password);
        $this->startSession($user, $request);

        return $this->me();
    }

    public function createAccount(string $email, string $password): User
    {
        if ($this->emailTaken->execute($email)) {
            throw new ApiException('email_taken', 409);
        }

        return DB::transaction(function () use ($email, $password): User {
            $user = $this->createUser->execute($email, $password);
            $this->workspaces->createForOwner($user->id, $email);

            return $user;
        });
    }

    public function login(LoginData $data, Request $request): MeData
    {
        $emailKey = 'login:email:'.$data->email;
        $ipKey = 'login:ip:'.$request->ip();
        $window = config('content.auth.login_window_minutes') * 60;
        if (RateLimiter::tooManyAttempts($emailKey, config('content.auth.max_login_failures_per_email'))
            || RateLimiter::tooManyAttempts($ipKey, config('content.auth.max_login_failures_per_ip'))) {
            throw new ApiException('too_many_attempts', 429);
        }
        if (! $this->guard()->attempt(['email' => $data->email, 'password' => $data->password])) {
            RateLimiter::hit($emailKey, $window);
            RateLimiter::hit($ipKey, $window);
            throw new ApiException('invalid_credentials', 401);
        }
        RateLimiter::clear($emailKey);
        $request->session()->regenerate();
        $this->recordLogin->execute($this->guard()->id());

        return $this->me();
    }

    public function logout(Request $request): void
    {
        $this->guard()->logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();
    }

    public function me(): MeData
    {
        $user = $this->guard()->user();

        return new MeData(new UserData($user->id, $user->email), $this->currentWorkspace->get());
    }

    private function startSession(User $user, Request $request): void
    {
        $this->guard()->login($user);
        $request->session()->regenerate();
        $this->recordLogin->execute($user->id);
    }

    private function guard(): StatefulGuard
    {
        return Auth::guard('web');
    }
}
