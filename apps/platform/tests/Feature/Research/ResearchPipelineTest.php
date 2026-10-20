<?php

namespace Tests\Feature\Research;

use Illuminate\Support\Facades\Queue;
use Modules\Pipeline\Services\JobRunner;
use Modules\Research\Models\ResearchSource;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ResearchPipelineTest extends TestCase
{
    use BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    private static function extraction(string $url, bool $ok = true): array
    {
        return [
            'url' => $url, 'source_type' => 'news', 'source_score' => 70, 'fetch_status' => $ok ? 'success' : 'failed',
            'http_status' => $ok ? 200 : 404, 'error' => $ok ? null : 'HTTP 404', 'title' => 'Tytuł', 'publisher' => 'Wydawca',
            'published_at' => '2026-06-01T00:00:00+00:00', 'extracted_content' => $ok ? 'Treść źródła' : null, 'raw_content' => $ok ? '<p>raw</p>' : null,
        ];
    }

    private function fakes(): array
    {
        return [
            'research.extract' => fn (array $request) => self::aiOk(['sources' => array_map(fn ($url) => self::extraction($url), $request['input']['urls'])]),
            'research.discover' => self::aiOk(['queries' => ['q1'], 'sources' => [self::extraction('https://docs.example.com/a')]], [self::llmCall('discovering_sources', '0.000100')]),
            'research.analyse' => fn (array $request) => self::aiOk([
                'summary' => 'Podsumowanie', 'why_it_matters' => 'Ważne', 'suggested_angle' => 'Kąt',
                'uncertainties' => [['claim' => 'X', 'reason' => 'brak']], 'conflicts' => [],
                'facts' => [['claim' => 'Fakt', 'importance' => 'critical', 'confidence' => 90, 'source_ids' => array_column($request['input']['sources'], 'id')]],
                'source_updates' => array_map(fn ($s) => ['id' => $s['id'], 'source_type' => 'official', 'source_score' => 100, 'publisher' => 'Pub'], $request['input']['sources']),
            ], [self::llmCall('analysing', '0.002000', 'gpt-research')]),
        ];
    }

    #[Test]
    public function research_fetches_discovers_analyses_and_stores_report(): void
    {
        $this->fakeAi($this->fakes());
        $candidate = $this->makeCandidate(['external_url' => 'https://example.com/news/1']);

        $this->getJson("/api/candidates/{$candidate->id}/research")->assertNotFound()->assertExactJson(['detail' => 'Research not found']);
        $jobId = $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202)->json('id');

        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'succeeded')->assertJsonPath('result.type', 'research');
        $research = $this->getJson("/api/candidates/{$candidate->id}/research")->assertOk()
            ->assertJsonPath('status', 'completed')->assertJsonPath('summary', 'Podsumowanie')
            ->assertJsonPath('search_queries', ['q1'])->assertJsonPath('llm_model', 'gpt-research')
            ->assertJsonPath('estimated_cost_usd', '0.002100')->assertJsonCount(2, 'sources')
            ->assertJsonPath('facts.0.claim', 'Fakt')->json();
        $this->assertSame(['original', 'search'], array_column($research['sources'], 'origin'));
        $this->assertSame(array_column($research['sources'], 'id'), $research['facts'][0]['source_ids']);
        $this->assertArrayNotHasKey('raw_content', $research['sources'][0]);
        $this->assertSame(['research.extract', 'research.discover', 'research.analyse'], array_column($this->aiRequests, 'task'));
        $this->assertSame('<p>raw</p>', $this->aiRequests[1]['input']['original_raw_content']);
    }

    #[Test]
    public function retry_reanalyses_existing_sources_without_discovery(): void
    {
        $this->fakeAi($this->fakes());
        $candidate = $this->makeCandidate();
        $this->postJson("/api/candidates/{$candidate->id}/research/retry")->assertStatus(404)
            ->assertExactJson(['detail' => 'Research not found - start a research first']);
        $this->postJson("/api/candidates/{$candidate->id}/research");
        $this->aiRequests = [];

        $this->postJson("/api/candidates/{$candidate->id}/research/retry")->assertStatus(202);
        $this->assertSame(['research.analyse'], array_column($this->aiRequests, 'task'));
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonCount(1, 'facts');
    }

    #[Test]
    public function paid_steps_are_not_repeated_when_job_is_retried(): void
    {
        Queue::fake();
        $fakes = $this->fakes();
        $fakes['research.analyse'] = self::aiError('llm_http_503', retryable: true);
        $this->fakeAi($fakes);
        $candidate = $this->makeCandidate();
        $jobId = $this->postJson("/api/candidates/{$candidate->id}/research")->json('id');

        app(JobRunner::class)->run($jobId);
        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'retrying');
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonPath('status', 'running');

        $this->fakeAi($this->fakes());
        app(JobRunner::class)->run($jobId);
        $this->assertSame(['research.analyse'], array_column($this->aiRequests, 'task'));
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonPath('status', 'completed')->assertJsonCount(2, 'sources');
    }

    #[Test]
    public function final_failure_marks_research_failed(): void
    {
        $fakes = $this->fakes();
        $fakes['research.analyse'] = ['ok' => false, 'error' => ['code' => 'no_source_content', 'message' => 'Brak treści', 'retryable' => false], 'calls' => []];
        $this->fakeAi($fakes);
        $candidate = $this->makeCandidate();

        $jobId = $this->postJson("/api/candidates/{$candidate->id}/research")->json('id');
        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'failed')->assertJsonPath('error_code', 'no_source_content');
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonPath('status', 'failed')->assertJsonPath('error', 'Brak treści');
    }

    #[Test]
    public function manual_source_is_fetched_and_deduplicated(): void
    {
        $this->fakeAi($this->fakes());
        $candidate = $this->makeCandidate();

        $this->postJson("/api/candidates/{$candidate->id}/research/sources", ['url' => 'https://www.example.org/page/?utm_source=x'])
            ->assertCreated()->assertJsonPath('origin', 'manual')->assertJsonPath('fetch_status', 'success');
        $this->postJson("/api/candidates/{$candidate->id}/research/sources", ['url' => 'https://example.org/page'])
            ->assertStatus(409)->assertExactJson(['detail' => 'This URL is already a source of this research']);
        $this->postJson("/api/candidates/{$candidate->id}/research/sources", ['url' => 'not a url'])->assertStatus(422);

        $this->postJson("/api/candidates/{$candidate->id}/research");
        $this->assertSame(['manual', 'original', 'search'], ResearchSource::query()->orderBy('id')->pluck('origin')->map->value->all());
    }
}
