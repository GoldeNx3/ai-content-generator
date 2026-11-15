<?php

namespace Tests\Feature\Auth;

use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\RateLimiter;
use Modules\Auth\Models\User;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class ChangePasswordTest extends TestCase
{
    private const NEW_PASSWORD = 'new correct horse battery';

    private function change(array $overrides = [])
    {
        return $this->spa()->postJson('/api/auth/password', [
            'current_password' => 'secret-password',
            'password' => self::NEW_PASSWORD,
            'password_confirmation' => self::NEW_PASSWORD,
            ...$overrides,
        ]);
    }

    #[Test]
    public function requires_a_session(): void
    {
        $this->spa()->postJson('/api/auth/password', [])->assertStatus(401);
    }

    #[Test]
    public function changes_the_password_after_verifying_the_current_one(): void
    {
        $user = $this->signIn();

        $this->change()->assertNoContent();

        $this->assertTrue(Hash::check(self::NEW_PASSWORD, $user->fresh()->password));
        $this->assertFalse(Hash::check('secret-password', $user->fresh()->password));
    }

    #[Test]
    public function wrong_current_password_is_rejected_without_logging_out(): void
    {
        $user = $this->signIn();

        $this->change(['current_password' => 'not-my-password'])
            ->assertStatus(422)
            ->assertExactJson(['detail' => ['code' => 'invalid_current_password']]);

        $this->assertTrue(Hash::check('secret-password', $user->fresh()->password));
    }

    #[Test]
    public function validates_the_new_password(): void
    {
        $this->signIn();

        $this->change(['password' => 'short', 'password_confirmation' => 'short'])->assertStatus(422);
        $this->change(['password_confirmation' => 'something else entirely'])->assertStatus(422);
        $this->change(['password' => 'secret-password', 'password_confirmation' => 'secret-password'])->assertStatus(422);
    }

    #[Test]
    public function repeated_wrong_attempts_are_throttled(): void
    {
        $user = $this->signIn();
        RateLimiter::clear('password:user:'.$user->id);

        for ($i = 0; $i < config('content.auth.max_login_failures_per_email'); $i++) {
            $this->change(['current_password' => 'wrong-password-'.$i])->assertStatus(422);
        }

        $this->change()->assertStatus(429)->assertJsonPath('detail.code', 'too_many_attempts');
        $this->assertTrue(Hash::check('secret-password', $user->fresh()->password));
    }

    #[Test]
    public function sessions_with_the_old_password_are_logged_out(): void
    {
        $user = $this->signIn();
        $oldHash = Auth::guard('web')->hashPasswordForCookie($user->password);

        $this->change()->assertNoContent();

        $fresh = User::query()->findOrFail($user->id);
        $newHash = Auth::guard('web')->hashPasswordForCookie($fresh->password);

        $this->actingAs($fresh, 'web');
        $this->spa()->withSession(['password_hash_web' => $newHash])->getJson('/api/auth/me')->assertOk();

        $this->actingAs($fresh, 'web');
        $this->spa()->withSession(['password_hash_web' => $oldHash])->getJson('/api/auth/me')->assertStatus(401);
    }
}
