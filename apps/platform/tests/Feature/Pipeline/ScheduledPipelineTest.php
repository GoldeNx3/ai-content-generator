<?php

namespace Tests\Feature\Pipeline;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ScheduledPipelineTest extends TestCase
{
    use BuildsDomain, FakesAi;

    private const SCORES = ['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'];

    protected function setUp(): void
    {
        parent::setUp();
        CarbonImmutable::setTestNow('2026-11-14 12:00:00');
        $this->signIn();
        Http::preventStrayRequests();
        Http::fake(['https://example.com/feed.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/rss.xml')))]);
        config(['content.ingestion.fetch_max_age_days' => 0]);
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
    }

    private function automate(array $settings, ?int $workspaceId = null): void
    {
        Workspace::query()->whereKey($workspaceId ?? $this->workspace->id)->update($settings);
    }

    private function settings(?int $workspaceId = null): Workspace
    {
        return Workspace::query()->find($workspaceId ?? $this->workspace->id);
    }

    #[Test]
    public function disabled_workspaces_are_not_touched(): void
    {
        $this->makeSource();

        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(0, Candidate::query()->count());
        $this->assertNull($this->settings()->last_auto_run_at);
    }

    #[Test]
    public function due_workspace_runs_once_per_interval(): void
    {
        $this->makeSource();
        $this->automate(['auto_fetch_enabled' => true, 'auto_fetch_interval_minutes' => 30, 'last_auto_run_at' => '2026-11-07 12:00:00']);

        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(2, Candidate::query()->count());
        $this->assertSame('2026-11-14 12:00:00', $this->settings()->last_auto_run_at->toDateTimeString());
        $this->assertSame(2, $this->settings()->last_auto_run_result['new_candidates']);

        $this->travel(29)->minutes();
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame('2026-11-14 12:00:00', $this->settings()->last_auto_run_at->toDateTimeString());

        $this->travel(1)->minutes();
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame('2026-11-14 12:30:00', $this->settings()->last_auto_run_at->toDateTimeString());
    }

    #[Test]
    public function classification_only_when_enabled_and_limited(): void
    {
        $this->makeSource();
        $this->automate(['auto_fetch_enabled' => true]);
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(0, PipelineJob::query()->count());
        $this->assertSame(0, $this->settings()->last_auto_run_result['enqueued']);

        $this->automate(['auto_classify_enabled' => true, 'auto_classify_batch_limit' => 1, 'last_auto_run_at' => null]);
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(1, PipelineJob::query()->count());
        $this->assertSame(1, $this->settings()->last_auto_run_result['enqueued']);
    }

    #[Test]
    public function paused_workspace_is_skipped_and_manual_run_fails(): void
    {
        $this->makeSource();
        $this->automate(['auto_fetch_enabled' => true, 'paused_at' => now()]);

        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->artisan('pipeline:scheduled', ['--email' => $this->user->email])->expectsOutputToContain('wstrzymany')->assertFailed();

        $this->assertSame(0, Candidate::query()->count());
    }

    #[Test]
    public function manual_run_ignores_disabled_automation(): void
    {
        $this->makeSource();
        $this->automate(['auto_classify_batch_limit' => 1]);

        $this->artisan('pipeline:scheduled', ['--workspace' => (string) $this->workspace->id])->assertSuccessful();

        $this->assertSame(2, Candidate::query()->count());
        $this->assertSame(1, PipelineJob::query()->count());
        $this->assertNull($this->settings()->last_auto_run_at);
    }

    #[Test]
    public function command_without_options_runs_due_workspaces_only(): void
    {
        $other = $this->otherWorkspace();
        $this->makeSource();
        $this->makeSource($other->id);
        $this->automate(['auto_fetch_enabled' => true], $other->id);

        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(0, Candidate::query()->where('workspace_id', $this->workspace->id)->count());
        $this->assertSame(2, Candidate::query()->where('workspace_id', $other->id)->count());
    }

    #[Test]
    public function budget_and_missing_key_still_respected(): void
    {
        $this->makeSource();
        $this->automate(['auto_fetch_enabled' => true, 'auto_classify_enabled' => true, 'monthly_budget_usd' => '0']);
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(0, PipelineJob::query()->count());
        $this->assertTrue($this->settings()->last_auto_run_result['budget_exceeded']);

        config(['content.ai.openai_api_key' => '']);
        $this->automate(['monthly_budget_usd' => null, 'last_auto_run_at' => null]);
        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(0, PipelineJob::query()->count());
    }

    #[Test]
    public function global_switch_off_runs_nothing(): void
    {
        config(['content.automation.enabled' => false]);
        $this->makeSource();
        $this->automate(['auto_fetch_enabled' => true]);

        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(0, Candidate::query()->count());
    }
}
