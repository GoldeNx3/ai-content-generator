<?php

namespace Tests;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Modules\Auth\Models\User;
use Modules\Workspaces\Models\Workspace;
use Modules\Workspaces\Models\WorkspaceMember;

abstract class TestCase extends BaseTestCase
{
    use RefreshDatabase;

    protected Workspace $workspace;

    protected User $user;

    protected function signIn(): User
    {
        $this->workspace = Workspace::query()->create(['name' => 'test']);
        $this->user = User::query()->create(['email' => fake()->unique()->safeEmail(), 'password' => 'secret-password']);
        WorkspaceMember::query()->create(['workspace_id' => $this->workspace->id, 'user_id' => $this->user->id, 'role' => 'owner']);
        $this->app->forgetScopedInstances();
        $this->actingAs($this->user, 'web');

        return $this->user;
    }

    protected function otherWorkspace(): Workspace
    {
        return Workspace::query()->create(['name' => 'obcy']);
    }

    protected function spa(): static
    {
        return $this->withHeaders(['Origin' => 'http://localhost:3000', 'Referer' => 'http://localhost:3000/']);
    }
}
