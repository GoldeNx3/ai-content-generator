<?php

namespace Tests\Feature\Workspaces;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class AutomationSettingsTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        CarbonImmutable::setTestNow('2026-11-14 12:00:00');
        $this->signIn();
    }

    #[Test]
    public function defaults_are_off(): void
    {
        $this->getJson('/api/workspace/automation')->assertOk()
            ->assertJsonPath('auto_fetch_enabled', false)
            ->assertJsonPath('auto_fetch_interval_minutes', 60)
            ->assertJsonPath('auto_classify_enabled', false)
            ->assertJsonPath('auto_classify_batch_limit', 20)
            ->assertJsonPath('next_auto_run_at', null)
            ->assertJsonPath('paused_at', null)
            ->assertJsonPath('automation_enabled_globally', true)
            ->assertJsonMissingPath('can_edit');
    }

    #[Test]
    public function owner_updates_and_next_run_is_computed(): void
    {
        $this->patchJson('/api/workspace/automation', ['auto_fetch_enabled' => true, 'auto_fetch_interval_minutes' => 30])->assertOk()
            ->assertJsonPath('auto_fetch_enabled', true)
            ->assertJsonPath('auto_fetch_interval_minutes', 30)
            ->assertJsonPath('auto_classify_enabled', false)
            ->assertJsonPath('next_auto_run_at', '2026-11-14T12:00:00+00:00');

        Workspace::query()->whereKey($this->workspace->id)->update(['last_auto_run_at' => '2026-11-14 11:50:00']);
        $this->getJson('/api/workspace/automation')->assertJsonPath('next_auto_run_at', '2026-11-14T12:20:00+00:00');

        $this->postJson('/api/workspace/pause')->assertOk();
        $this->getJson('/api/workspace/automation')->assertJsonPath('next_auto_run_at', null)->assertJsonPath('paused_at', '2026-11-14T12:00:00+00:00');
    }

    #[Test]
    public function invalid_values_are_rejected(): void
    {
        $this->patchJson('/api/workspace/automation', ['auto_fetch_interval_minutes' => 45])->assertStatus(422)
            ->assertJsonPath('detail.0.loc.1', 'auto_fetch_interval_minutes');
        $this->patchJson('/api/workspace/automation', ['auto_classify_batch_limit' => 0])->assertStatus(422);
        $this->patchJson('/api/workspace/automation', ['auto_classify_batch_limit' => 201])->assertStatus(422);
        $this->patchJson('/api/workspace/automation', ['auto_fetch_enabled' => 'tak'])->assertStatus(422);

        $this->assertSame(60, Workspace::query()->find($this->workspace->id)->auto_fetch_interval_minutes);
    }

    #[Test]
    public function settings_belong_to_one_account_only(): void
    {
        $other = Workspace::query()->create(['name' => 'inne konto', 'auto_fetch_enabled' => true, 'auto_fetch_interval_minutes' => 15]);

        $this->getJson('/api/workspace/automation')->assertJsonPath('auto_fetch_enabled', false)->assertJsonPath('auto_fetch_interval_minutes', 60);
        $this->patchJson('/api/workspace/automation', ['auto_fetch_interval_minutes' => 1440])->assertOk();

        $this->assertSame(15, $other->fresh()->auto_fetch_interval_minutes);
        $this->assertTrue($other->fresh()->auto_fetch_enabled);
    }

    #[Test]
    public function global_switch_is_reported(): void
    {
        config(['content.automation.enabled' => false]);
        Workspace::query()->whereKey($this->workspace->id)->update(['auto_fetch_enabled' => true]);

        $this->getJson('/api/workspace/automation')->assertJsonPath('automation_enabled_globally', false)->assertJsonPath('next_auto_run_at', null);
    }
}
