<?php

namespace Tests\Feature\Articles;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\WordPress\Models\WordPressConnection;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\Support\FakeWordPress;
use Tests\TestCase;

final class RefreshPostTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private const SCORES = ['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'];

    private FakeWordPress $wp;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        config(['content.wordpress.allow_private_urls' => true]);
        $this->wp = new FakeWordPress;
        $this->wp->published = [['id' => 11, 'link' => 'https://wp.example/blog/kolejki-w-laravel/', 'title' => 'Kolejki w Laravel – jak je monitorować',
            'excerpt' => 'Horizon.', 'content' => '<h2>Horizon</h2><p>Laravel 12 ma <strong>kolejki</strong> z priorytetami.</p>']];
        Http::preventStrayRequests();
        Http::fake(fn ($request) => $this->wp->handle($request));
        WordPressConnection::query()->create(['workspace_id' => $this->workspace->id, 'site_url' => 'https://wp.example/blog', 'username' => 'editor',
            'app_password' => 'secret', 'instance_id' => 'ce-test', 'seo_plugin' => 'yoast']);
        $this->postJson('/api/wordpress/posts/sync')->assertOk();
    }

    private function coveredCandidate(): Candidate
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $candidate = $this->makeCandidate(['title' => 'Kolejki w Laravel - jak je monitorować']);
        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(202);

        return $candidate->refresh();
    }

    #[Test]
    public function the_covering_blog_post_is_remembered_on_the_topic(): void
    {
        $candidate = $this->coveredCandidate();

        $this->getJson("/api/candidates/{$candidate->id}")
            ->assertJsonPath('covered_by.type', 'post')->assertJsonPath('covered_by.post_id', 11)
            ->assertJsonPath('covered_by.url', 'https://wp.example/blog/kolejki-w-laravel/')
            ->assertJsonPath('covered_by.title', 'Kolejki w Laravel – jak je monitorować');
    }

    #[Test]
    public function a_published_article_covering_the_topic_points_to_its_post(): void
    {
        $old = $this->makeCandidate(['title' => 'Stary temat']);
        $article = $this->makeArticle($old, ['title' => 'Nowy model – analiza']);
        DB::table('articles')->where('id', $article->id)->update(['embedding' => '{1,0,0}', 'embedding_model' => 'text-embedding-3-small']);
        DB::table('wordpress_publications')->insert(['candidate_id' => $old->id, 'article_version_id' => $article->id, 'wordpress_post_id' => 77,
            'wordpress_instance_id' => 'ce-test', 'wordpress_url' => 'https://wp.example/blog/nowy-model/', 'status' => 'synced', 'created_at' => now(), 'updated_at' => now()]);
        $this->fakeAi(['embed' => self::aiOk(['vectors' => [[1.0, 0.0, 0.0]], 'model' => 'text-embedding-3-small']), 'classify' => self::aiOk(self::SCORES)]);
        $candidate = $this->makeCandidate(['title' => 'Nowy model']);

        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(202);

        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('covered_by.type', 'article')
            ->assertJsonPath('covered_by.article_id', $article->id)->assertJsonPath('covered_by.post_id', 77)
            ->assertJsonPath('covered_by.url', 'https://wp.example/blog/nowy-model/');
    }

    #[Test]
    public function a_refresh_hands_the_old_post_to_the_writer_and_remembers_it_on_the_version(): void
    {
        $candidate = $this->coveredCandidate();
        $this->completedResearch($candidate);
        $this->fakeAi([
            'article.brief' => self::aiOk(['context' => ['candidate_title' => 'T'], 'brief' => ['article_format' => 'news'], 'warnings' => []]),
            'article.write' => fn () => self::aiOk(self::writtenArticle()),
            'article.rebuild' => fn (array $request) => self::aiOk(['sections' => [], 'sections_count' => 0, 'facts_used_count' => 0, 'source_count' => 0, 'word_count' => 3]),
            'seo.preview' => self::aiOk(['seo_preview' => [], 'seo_origin' => 'article']),
        ]);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto', 'refresh' => true])->assertStatus(202);

        $brief = collect($this->aiRequests)->firstWhere('task', 'article.brief')['input'];
        $this->assertSame(['title' => 'Kolejki w Laravel – jak je monitorować', 'url' => 'https://wp.example/blog/kolejki-w-laravel/',
            'content' => "Horizon\n\nLaravel 12 ma kolejki z priorytetami."], $brief['refresh_of']);
        $this->assertArrayNotHasKey('refresh', $brief['request']);
        $this->getJson("/api/candidates/{$candidate->id}/articles")->assertJsonPath('0.refresh_of.post_id', 11)
            ->assertJsonPath('0.refresh_of.url', 'https://wp.example/blog/kolejki-w-laravel/');
    }

    #[Test]
    public function a_refresh_needs_a_covering_post(): void
    {
        $candidate = $this->makeCandidate();
        $this->completedResearch($candidate);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto', 'refresh' => true])->assertStatus(422);
    }

    #[Test]
    public function an_unreachable_old_post_fails_before_any_paid_call(): void
    {
        $candidate = $this->coveredCandidate();
        $this->completedResearch($candidate);
        $this->wp->published = [];
        $this->aiRequests = [];

        $job = $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto', 'refresh' => true])->assertStatus(202)->json('id');

        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'failed')->assertJsonPath('error_code', 'refresh_post_unavailable');
        $this->assertSame([], $this->aiRequests);
    }
}
