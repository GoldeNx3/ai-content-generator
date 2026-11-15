<?php

namespace Tests\Feature\Pipeline;

use Carbon\CarbonImmutable;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class PipelineHealthTest extends TestCase
{
    use BuildsDomain;

    private const SLACK = 'https://hooks.slack.com/services/T/B/x';

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        CarbonImmutable::setTestNow('2026-11-20 12:00:00');
        config(['content.alerts.webhook_url' => self::SLACK, 'content.frontend_url' => 'https://panel.example']);
        Http::preventStrayRequests();
        Http::fake(['hooks.slack.com/*' => Http::response('ok'), 'discord.com/*' => Http::response('', 204)]);
    }

    private function check(): void
    {
        $this->artisan('pipeline:health')->assertSuccessful();
    }

    private function messages(): array
    {
        return array_map(fn (array $pair) => $pair[0]['text'] ?? $pair[0]['content'], Http::recorded()->all());
    }

    private function stalledJob(): void
    {
        $this->makeJob(['status' => 'queued', 'available_at' => now()->subMinutes(12)]);
    }

    #[Test]
    public function a_queue_nobody_picks_up_raises_one_alert_until_it_recovers(): void
    {
        $this->stalledJob();
        $this->makeJob(['status' => 'queued', 'available_at' => now()->subMinute()]);

        $this->check();
        $this->check();

        $this->assertCount(1, $this->messages());
        $this->assertStringContainsString('1 zadanie czeka', $this->messages()[0]);
        $this->assertStringContainsString('12 min', $this->messages()[0]);
        $this->assertStringContainsString('https://panel.example/queue', $this->messages()[0]);

        DB::table('pipeline_jobs')->update(['status' => 'succeeded']);
        $this->check();
        $this->assertCount(2, $this->messages());
        $this->assertStringContainsString('wróciło do normy', $this->messages()[1]);
    }

    #[Test]
    public function the_alert_repeats_after_an_hour_while_the_problem_lasts(): void
    {
        $this->stalledJob();
        $this->check();
        CarbonImmutable::setTestNow('2026-11-20 13:01:00');

        $this->check();

        $this->assertCount(2, $this->messages());
    }

    #[Test]
    public function long_running_jobs_and_bursts_of_provider_errors_are_reported(): void
    {
        $this->makeJob(['status' => 'running', 'started_at' => now()->subMinutes(45)]);
        foreach (range(1, 5) as $number) {
            $job = $this->makeJob(['status' => 'retrying', 'available_at' => now()->addMinute()]);
            DB::table('pipeline_job_attempts')->insert(['pipeline_job_id' => $job->id, 'number' => 1, 'started_at' => now()->subMinutes(5),
                'finished_at' => now()->subMinutes(4), 'outcome' => 'retryable_error', 'error_code' => 'llm_http_429', 'llm_calls' => '[]']);
        }

        $this->check();

        $text = implode("\n", $this->messages());
        $this->assertStringContainsString('dłużej niż 30 min', $text);
        $this->assertStringContainsString('5 błędów dostawcy', $text);
        $this->assertStringContainsString('llm_http_429', $text);
    }

    #[Test]
    public function paused_accounts_healthy_queues_and_missing_webhooks_send_nothing(): void
    {
        DB::table('workspaces')->where('id', $this->workspace->id)->update(['paused_at' => now()]);
        $this->stalledJob();
        $this->check();
        $this->assertSame([], $this->messages());

        DB::table('workspaces')->update(['paused_at' => null]);
        config(['content.alerts.webhook_url' => '']);
        $this->check();
        $this->assertSame([], $this->messages());
    }

    #[Test]
    public function discord_webhooks_get_their_own_payload_and_a_failing_webhook_does_not_break_the_check(): void
    {
        config(['content.alerts.webhook_url' => 'https://discord.com/api/webhooks/1/x']);
        $this->stalledJob();

        $this->check();

        Http::assertSent(fn (Request $request) => str_contains($request->url(), 'discord.com') && isset($request->data()['content']));
        Http::fake(['*' => Http::response('down', 500)]);
        CarbonImmutable::setTestNow('2026-11-20 14:00:00');
        $this->check();
    }
}
