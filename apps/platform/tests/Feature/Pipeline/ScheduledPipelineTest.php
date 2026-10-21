<?php

namespace Tests\Feature\Pipeline;

use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Models\PipelineJob;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ScheduledPipelineTest extends TestCase
{
    use BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        Http::preventStrayRequests();
        Http::fake(['https://example.com/feed.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/rss.xml')))]);
        config(['content.ingestion.fetch_max_age_days' => 0]);
    }

    #[Test]
    public function scheduler_fetches_and_classifies_per_workspace_with_budget(): void
    {
        $this->fakeAi(['classify' => self::aiOk(['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'])]);
        $this->makeSource();
        $poor = $this->otherWorkspace();
        $poor->update(['monthly_budget_usd' => '0']);
        $this->makeCandidate([], $poor->id);

        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(2, Candidate::query()->where('workspace_id', $this->workspace->id)->whereNotNull('total_score')->count());
        $this->assertSame(0, PipelineJob::query()->where('workspace_id', $poor->id)->count());

        $this->artisan('pipeline:scheduled')->assertSuccessful();
        $this->assertSame(2, PipelineJob::query()->count());
    }

    #[Test]
    public function scheduler_skips_classification_without_api_key(): void
    {
        config(['content.ai.openai_api_key' => '']);
        $this->makeSource();
        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(2, Candidate::query()->count());
        $this->assertSame(0, PipelineJob::query()->count());
    }
}
