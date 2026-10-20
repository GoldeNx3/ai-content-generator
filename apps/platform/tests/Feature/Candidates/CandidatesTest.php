<?php

namespace Tests\Feature\Candidates;

use Modules\Articles\Models\Article;
use Modules\WordPress\Models\WordPressPublication;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class CandidatesTest extends TestCase
{
    use BuildsDomain;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function list_filters_sorts_and_paginates_within_workspace(): void
    {
        $this->makeCandidate(['total_score' => 50, 'category' => 'news']);
        $top = $this->makeCandidate(['total_score' => 90, 'category' => 'guide']);
        $this->makeCandidate(['total_score' => null, 'status' => 'ignored']);
        $this->makeCandidate(['total_score' => 99], $this->otherWorkspace()->id);

        $page = $this->getJson('/api/candidates')->assertOk()->json();
        $this->assertSame(3, $page['total']);
        $this->assertSame($top->id, $page['items'][0]['id']);
        $this->assertNull($page['items'][2]['total_score']);
        $this->assertSame('ignored', $page['items'][2]['workflow_status']);

        $this->getJson('/api/candidates?category=guide')->assertJsonPath('total', 1);
        $this->getJson('/api/candidates?min_score=60')->assertJsonPath('total', 1);
        $this->getJson('/api/candidates?status=ignored')->assertJsonPath('total', 1);
        $this->getJson('/api/candidates?sort=total_score&order=asc&page=2&page_size=1')
            ->assertJsonPath('page', 2)->assertJsonPath('items.0.total_score', 90);
        $this->getJson('/api/candidates?page_size=500')->assertStatus(422);
        $this->getJson('/api/candidates?sort=title')->assertStatus(422);
    }

    #[Test]
    public function details_status_update_and_isolation(): void
    {
        $candidate = $this->makeCandidate(['summary' => 'Opis']);
        $foreign = $this->makeCandidate([], $this->otherWorkspace()->id);

        $this->getJson("/api/candidates/{$candidate->id}")->assertOk()
            ->assertJsonPath('source_name', $candidate->source->name)->assertJsonPath('is_demo', false)
            ->assertJsonPath('workflow_status', 'pending');
        $this->getJson("/api/candidates/{$foreign->id}")->assertNotFound()->assertExactJson(['detail' => ['code' => 'not_found']]);
        $this->patchJson("/api/candidates/{$candidate->id}/status", ['status' => 'approved'])
            ->assertOk()->assertJsonPath('status', 'approved')->assertJsonPath('workflow_status', 'approved');
        $this->patchJson("/api/candidates/{$candidate->id}/status", ['status' => 'bogus'])->assertStatus(422);
    }

    #[Test]
    public function workflow_status_follows_article_and_wordpress(): void
    {
        $candidate = $this->makeCandidate();
        $article = Article::query()->create([
            'candidate_id' => $candidate->id, 'version' => 1, 'title' => 'T', 'slug' => 't', 'lead' => 'L', 'content' => 'C',
            'generated_content' => 'C', 'meta_title' => 'T', 'meta_description' => 'D', 'article_type' => 'news',
            'brief' => [], 'sections' => [], 'generation_options' => [], 'research_snapshot' => [],
        ]);
        $this->getJson('/api/candidates?workflow_status=draft')->assertJsonPath('total', 1);

        $article->update(['status' => 'approved']);
        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('workflow_status', 'approved');

        WordPressPublication::query()->create([
            'candidate_id' => $candidate->id, 'article_version_id' => $article->id, 'wordpress_post_id' => 5,
            'wp_status' => 'future', 'last_synced_at' => now(),
        ]);
        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('workflow_status', 'scheduled');
        $this->getJson('/api/candidates?workflow_status=scheduled')->assertJsonPath('total', 1);
    }

    #[Test]
    public function dashboard_stats_are_scoped(): void
    {
        $this->makeCandidate(['total_score' => 80, 'status' => 'approved']);
        $this->makeCandidate(['total_score' => 61]);
        $this->makeCandidate(['status' => 'ignored']);
        $this->makeCandidate(['total_score' => 10], $this->otherWorkspace()->id);

        $this->getJson('/api/stats')->assertOk()->assertExactJson([
            'candidates_today' => 3, 'new_today' => 1, 'approved' => 1, 'ignored' => 1, 'average_score' => 70.5,
        ]);
    }
}
