<?php

namespace Tests\Feature\Auth;

use Illuminate\Contracts\Console\Kernel;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\RateLimiter;
use Modules\Auth\Models\User;
use Modules\Workspaces\Models\WorkspaceMember;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class AuthTest extends TestCase
{
    private const PASSWORD = 'correct horse battery';

    private function register(string $email = 'Jan@Example.com', string $password = self::PASSWORD)
    {
        return $this->spa()->postJson('/api/auth/register', ['email' => $email, 'password' => $password]);
    }

    #[Test]
    public function protected_endpoint_requires_session(): void
    {
        $this->getJson('/api/auth/me')->assertStatus(401)->assertExactJson(['detail' => ['code' => 'not_authenticated']]);
    }

    #[Test]
    public function register_creates_owner_workspace_and_logs_in(): void
    {
        $this->register()->assertCreated()
            ->assertJsonPath('user.email', 'jan@example.com')
            ->assertJsonMissingPath('workspace.role')
            ->assertJsonPath('workspace.name', 'jan');

        $this->spa()->getJson('/api/auth/me')->assertOk()->assertJsonPath('user.email', 'jan@example.com');
        $user = User::query()->where('email', 'jan@example.com')->firstOrFail();
        $this->assertNotSame(self::PASSWORD, $user->password);
        $this->assertTrue(password_verify(self::PASSWORD, $user->password));
        $this->assertSame(1, WorkspaceMember::query()->where('user_id', $user->id)->count());
    }

    #[Test]
    public function every_account_is_its_own_tenant(): void
    {
        $this->artisan('users:create', ['email' => 'a@example.com'])->expectsQuestion('Hasło (min. 10 znaków)', self::PASSWORD)->assertSuccessful();
        $this->artisan('users:create', ['email' => 'b@example.com'])->expectsQuestion('Hasło (min. 10 znaków)', self::PASSWORD)->assertSuccessful();

        $workspaces = WorkspaceMember::query()->pluck('workspace_id', 'user_id');
        $this->assertCount(2, $workspaces);
        $this->assertCount(2, $workspaces->unique());
        $this->assertArrayNotHasKey('workspace', $this->app->make(Kernel::class)->all()['users:create']->getDefinition()->getOptions());
    }

    #[Test]
    public function database_refuses_a_second_member_or_a_second_workspace(): void
    {
        $this->signIn();
        $second = User::query()->create(['email' => 'drugi@example.com', 'password' => 'secret-password']);

        $other = $this->otherWorkspace();
        $insert = fn (array $row) => fn () => DB::transaction(fn () => WorkspaceMember::query()->create([...$row, 'role' => 'owner']));

        $this->assertThrows($insert(['workspace_id' => $this->workspace->id, 'user_id' => $second->id]), UniqueConstraintViolationException::class);
        $this->assertThrows($insert(['workspace_id' => $other->id, 'user_id' => $this->user->id]), UniqueConstraintViolationException::class);
    }

    #[Test]
    public function one_workspace_migration_refuses_shared_workspaces_and_changes_nothing(): void
    {
        $this->signIn();
        $second = User::query()->create(['email' => 'drugi@example.com', 'password' => 'secret-password']);
        DB::statement('DROP INDEX uq_workspace_members_user');
        DB::statement('DROP INDEX uq_workspace_members_workspace');
        WorkspaceMember::query()->create(['workspace_id' => $this->workspace->id, 'user_id' => $second->id, 'role' => 'owner']);
        DB::table('workspace_members')->where('user_id', $second->id)->update(['role' => 'member']);
        $migration = require base_path('src/Workspaces/Database/Migrations/2026_11_15_000001_one_account_one_workspace.php');

        $this->assertThrows(fn () => $migration->up(), \RuntimeException::class, "shared workspaces [{$this->workspace->id}]");

        $this->assertSame('member', DB::table('workspace_members')->where('user_id', $second->id)->value('role'));
        $this->assertSame(0, DB::table('pg_indexes')->where('indexname', 'uq_workspace_members_user')->count());
    }

    #[Test]
    public function register_validates_input_and_rejects_duplicates(): void
    {
        $this->register(password: 'short')->assertStatus(422)->assertJsonPath('detail.0.loc', ['body', 'password']);
        $this->register(email: 'not-an-email')->assertStatus(422)->assertJsonPath('detail.0.loc', ['body', 'email']);
        $this->register();
        $this->app['auth']->guard('web')->logout();
        $this->register(email: ' JAN@example.com ')->assertStatus(409)->assertExactJson(['detail' => ['code' => 'email_taken']]);
    }

    #[Test]
    public function registration_can_be_disabled(): void
    {
        config(['content.allow_registration' => false]);

        $this->register()->assertStatus(403)->assertExactJson(['detail' => ['code' => 'registration_disabled']]);
    }

    #[Test]
    public function registration_is_limited_per_ip(): void
    {
        config(['content.auth.max_registrations_per_ip' => 2]);
        $this->register('a@example.com')->assertCreated();
        $this->register('a@example.com')->assertStatus(409);
        $this->register('b@example.com')->assertStatus(429)->assertExactJson(['detail' => ['code' => 'too_many_registrations']]);
    }

    #[Test]
    public function login_logout_and_wrong_password(): void
    {
        $this->register();
        $this->app['auth']->guard('web')->logout();

        $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => 'nope'])
            ->assertStatus(401)->assertExactJson(['detail' => ['code' => 'invalid_credentials']]);
        $this->spa()->postJson('/api/auth/login', ['email' => 'nikt@example.com', 'password' => 'x'])->assertStatus(401);
        $this->spa()->postJson('/api/auth/login', ['email' => 'JAN@example.com', 'password' => self::PASSWORD])
            ->assertOk()->assertJsonMissingPath('workspace.role');
        $this->spa()->getJson('/api/auth/me')->assertOk();

        $this->spa()->postJson('/api/auth/logout')->assertNoContent();
        $this->app['auth']->forgetGuards();
        $this->spa()->getJson('/api/auth/me')->assertStatus(401);
    }

    #[Test]
    public function failed_logins_from_one_address_do_not_lock_the_owner_out_elsewhere(): void
    {
        $this->register();
        $this->app['auth']->guard('web')->logout();
        config(['content.auth.max_login_failures_per_email' => 3]);
        foreach (range(1, 3) as $_) {
            $this->spa()->withServerVariables(['REMOTE_ADDR' => '203.0.113.9'])->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => 'bad']);
        }

        $this->spa()->withServerVariables(['REMOTE_ADDR' => '203.0.113.9'])->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])
            ->assertStatus(429);
        $this->spa()->withServerVariables(['REMOTE_ADDR' => '198.51.100.20'])->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])
            ->assertOk();
        RateLimiter::clear('login:email:jan@example.com|203.0.113.9');
    }

    #[Test]
    public function login_is_throttled_per_email(): void
    {
        $this->register();
        $this->app['auth']->guard('web')->logout();
        config(['content.auth.max_login_failures_per_email' => 3]);
        foreach (range(1, 3) as $_) {
            $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => 'bad']);
        }

        $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])
            ->assertStatus(429)->assertExactJson(['detail' => ['code' => 'too_many_attempts']]);
        RateLimiter::clear('login:email:jan@example.com|127.0.0.1');
    }

    #[Test]
    public function login_records_last_login_time(): void
    {
        $this->register();
        $this->app['auth']->guard('web')->logout();
        User::query()->update(['last_login_at' => null]);

        $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])->assertOk();

        $this->assertNotNull(User::query()->where('email', 'jan@example.com')->value('last_login_at'));
    }

    #[Test]
    public function deactivated_account_cannot_log_in_and_loses_its_session(): void
    {
        $this->register();
        $this->spa()->getJson('/api/auth/me')->assertOk();

        $this->artisan('users:deactivate', ['email' => 'JAN@example.com'])->assertSuccessful();
        $this->app['auth']->forgetGuards();
        $this->spa()->getJson('/api/auth/me')->assertStatus(401)->assertExactJson(['detail' => ['code' => 'not_authenticated']]);
        $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])
            ->assertStatus(401)->assertExactJson(['detail' => ['code' => 'invalid_credentials']]);

        $this->artisan('users:activate', ['email' => 'jan@example.com'])->assertSuccessful();
        $this->app['auth']->forgetGuards();
        $this->spa()->postJson('/api/auth/login', ['email' => 'jan@example.com', 'password' => self::PASSWORD])->assertOk();
        $this->artisan('users:deactivate', ['email' => 'nikt@example.com'])->assertFailed();
    }
}
