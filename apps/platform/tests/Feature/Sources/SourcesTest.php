<?php

namespace Tests\Feature\Sources;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\Sources\Models\Source;
use Modules\Sources\Services\FeedReader;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class SourcesTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        CarbonImmutable::setTestNow('2025-10-05 12:00:00');
        Http::preventStrayRequests();
        Http::fake([
            'https://example.com/feed.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/rss.xml'))),
            'https://example.com/atom.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/atom.xml'))),
            'https://example.com/broken.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/broken.xml'))),
            'https://example.com/missing.xml' => Http::response('', 404),
        ]);
        $this->signIn();
    }

    private function source(string $url = 'https://example.com/feed.xml', ?int $workspaceId = null): Source
    {
        return Source::query()->create(['workspace_id' => $workspaceId ?? $this->workspace->id, 'name' => 'Feed '.$url, 'url' => $url]);
    }

    #[Test]
    public function parser_cleans_html_and_reads_dates(): void
    {
        $entries = app(FeedReader::class)->parse(file_get_contents(base_path('tests/Fixtures/rss.xml')));

        $this->assertCount(3, $entries);
        $this->assertSame('Big release today.', $entries[0]->summary);
        $this->assertSame('2025-10-01T10:00:00+00:00', $entries[0]->published_at->toIso8601String());
        $this->assertNull($entries[1]->published_at);
    }

    #[Test]
    public function crud_with_validation_and_workspace_scope(): void
    {
        $this->postJson('/api/sources', ['name' => 'Feed', 'url' => 'https://example.com/feed.xml'])
            ->assertCreated()->assertJsonPath('type', 'rss')->assertJsonPath('active', true);
        $this->postJson('/api/sources', ['name' => 'Dup', 'url' => 'https://example.com/feed.xml'])
            ->assertStatus(409)->assertExactJson(['detail' => 'Source with this URL already exists']);
        $this->postJson('/api/sources', ['name' => '', 'url' => 'ftp://x'])->assertStatus(422);

        $foreign = $this->source('https://example.com/feed.xml', $this->otherWorkspace()->id);
        $list = $this->getJson('/api/sources')->assertOk()->json();
        $this->assertCount(1, $list);
        $this->patchJson("/api/sources/{$foreign->id}", ['active' => false])->assertNotFound();

        $own = $list[0]['id'];
        $this->patchJson("/api/sources/{$own}", ['active' => false, 'name' => ' Nowa '])
            ->assertOk()->assertJsonPath('active', false)->assertJsonPath('name', 'Nowa');
        $this->deleteJson("/api/sources/{$own}")->assertNoContent();
    }

    #[Test]
    public function fetch_creates_candidates_dedupes_and_drops_old_entries(): void
    {
        $source = $this->source();

        $this->postJson("/api/sources/{$source->id}/fetch")->assertOk()->assertExactJson([
            'sources_processed' => 1, 'items_found' => 3, 'new_candidates' => 2, 'duplicates' => 1, 'skipped_old' => 0, 'errors' => 0,
        ]);
        $this->postJson("/api/sources/{$source->id}/fetch")->assertJsonPath('new_candidates', 0)->assertJsonPath('duplicates', 3);

        config(['content.ingestion.fetch_max_age_days' => 1]);
        $this->postJson('/api/sources/fetch')->assertJsonPath('skipped_old', 1);
        $this->assertNotNull($source->refresh()->last_fetched_at);
    }

    #[Test]
    public function fetch_all_counts_errors_and_only_touches_own_workspace(): void
    {
        $this->source('https://example.com/atom.xml');
        $this->source('https://example.com/broken.xml');
        $this->source('https://example.com/missing.xml');
        $this->source('https://example.com/feed.xml', $this->otherWorkspace()->id);

        $this->postJson('/api/sources/fetch')->assertOk()
            ->assertJsonPath('sources_processed', 3)->assertJsonPath('errors', 2)->assertJsonPath('new_candidates', 1);
        $this->assertSame([$this->workspace->id], Candidate::query()->distinct()->pluck('workspace_id')->all());
    }

    #[Test]
    public function same_feed_in_two_workspaces_gives_separate_candidates(): void
    {
        $foreign = $this->source('https://example.com/feed.xml', $this->otherWorkspace()->id);
        $own = $this->source();
        $this->postJson("/api/sources/{$own->id}/fetch")->assertJsonPath('new_candidates', 2);
        app(\Modules\Sources\Services\IngestionService::class)->fetchSource($foreign);

        $this->assertSame(4, Candidate::query()->count());
    }

    #[Test]
    public function source_with_job_history_cannot_be_deleted(): void
    {
        $source = $this->source();
        $this->postJson("/api/sources/{$source->id}/fetch");
        $candidate = Candidate::query()->firstOrFail();
        \Modules\Pipeline\Models\PipelineJob::query()->create([
            'workspace_id' => $this->workspace->id, 'candidate_id' => $candidate->id, 'kind' => 'classify',
            'status' => 'succeeded', 'payload' => [], 'idempotency_key' => (string) \Illuminate\Support\Str::uuid(), 'request_hash' => 'x',
        ]);

        $this->deleteJson("/api/sources/{$source->id}")->assertStatus(409);
    }
}
