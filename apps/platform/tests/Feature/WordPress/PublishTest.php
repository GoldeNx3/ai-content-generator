<?php

namespace Tests\Feature\WordPress;

use Illuminate\Support\Facades\Http;
use Modules\Articles\Models\Article;
use Modules\Qa\Models\ArticleQa;
use Modules\Qa\Support\QaSnapshot;
use Modules\WordPress\Models\WordPressConnection;
use Modules\WordPress\Models\WordPressPublication;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\Support\FakeWordPress;
use Tests\TestCase;

final class PublishTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private FakeWordPress $wp;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        config(['content.wordpress.allow_private_urls' => true]);
        $this->wp = new FakeWordPress;
        Http::preventStrayRequests();
        Http::fake(fn ($request) => $this->wp->handle($request));
        $profile = ['title' => 'Tytuł', 'slug' => 'tytul', 'seo_title' => 'Meta', 'meta_description' => 'Opis', 'excerpt' => 'E',
            'og_title' => 'Meta', 'og_description' => 'Opis', 'category' => 'Newsy', 'tags' => ['AI'], 'robots_index' => true,
            'robots_follow' => true, 'schema_type' => 'NewsArticle', 'canonical_url' => null];
        $this->fakeAi([
            'seo.profile' => fn ($r) => self::aiOk(['profile' => [...$profile, ...array_intersect_key($r['input']['overrides'], ['category' => 1, 'tags' => 1])]]),
            'seo.prepare' => self::aiOk(['profile' => $profile], [self::llmCall('preparing_seo')]),
            'wordpress.render' => self::aiOk(['html' => '<p>Lead.</p><h2>Sekcja</h2><p>Treść.</p>', 'slug' => 'tytul']),
            'wordpress.metadata' => fn ($r) => self::aiOk(['metadata' => ['_yoast_wpseo_title' => 'Meta', '_yoast_wpseo_canonical' => $r['input']['profile']['canonical_url']], 'warnings' => []]),
            'wordpress.verify_meta' => self::aiOk(['warnings' => []]),
        ]);
    }

    private function connect(): void
    {
        WordPressConnection::query()->create(['workspace_id' => $this->workspace->id, 'site_url' => 'https://wp.example/blog', 'username' => 'editor',
            'app_password' => 'secret', 'instance_id' => 'ce-test', 'seo_plugin' => 'yoast']);
    }

    private function approvedArticle(array $overrides = []): Article
    {
        $article = $this->makeArticle($this->makeCandidate(), ['status' => 'approved', ...$overrides]);
        $snapshot = QaSnapshot::build($article);
        ArticleQa::query()->create(['article_id' => $article->id, 'article_version' => 1, 'status' => 'completed', 'input_snapshot' => $snapshot,
            'input_hash' => QaSnapshot::hash($snapshot), 'overall_score' => 95, 'qa_passed' => true, 'pass_score' => 85]);

        return $article->refresh();
    }

    #[Test]
    public function draft_is_created_verified_and_linked(): void
    {
        $this->connect();
        $article = $this->approvedArticle();

        $job = $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'draft'])->assertStatus(202)->json('id');
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'succeeded')->assertJsonPath('result.type', 'wordpress_publication');

        $this->assertSame(1, $this->wp->creates);
        $post = $this->wp->posts[101];
        $this->assertSame('Meta', $post['meta']['_yoast_wpseo_title']);
        $this->assertSame([1], $post['categories']);
        $state = $this->getJson("/api/article-versions/{$article->id}/wordpress")->assertOk()
            ->assertJsonPath('publication.status', 'draft_created')->assertJsonPath('publication.wordpress_post_id', 101)
            ->assertJsonPath('remote_status', 'draft')->assertJsonPath('wordpress_connected', true)->json();
        $this->assertStringContainsString('post=101', $state['wordpress_admin_url']);
        $this->assertSame('approved', $article->candidate->refresh()->status->value);

        $this->postJson("/api/article-versions/{$article->id}/wordpress/sync", [])->assertStatus(202);
        $this->assertSame(1, $this->wp->creates);
    }

    #[Test]
    public function title_sent_to_wordpress_is_plain_text(): void
    {
        $this->connect();
        $article = $this->approvedArticle(['title' => '</title><script>alert(1)</script>Tytuł']);

        $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'draft'])->assertStatus(202);

        $this->assertStringNotContainsString('<', $this->wp->posts[101]['title']['raw']);
        $this->assertStringContainsString('Tytuł', $this->wp->posts[101]['title']['raw']);
    }

    #[Test]
    public function manual_wordpress_changes_cause_conflict(): void
    {
        $this->connect();
        $article = $this->approvedArticle();
        $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'draft']);
        $this->wp->posts[101]['content']['raw'] = 'Ręczna zmiana w WP';

        $job = $this->postJson("/api/article-versions/{$article->id}/wordpress/sync", [])->json('id');
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'failed')->assertJsonPath('error_code', 'wordpress_conflict');
        $this->getJson("/api/article-versions/{$article->id}/wordpress")->assertJsonPath('publication.status', 'failed')
            ->assertJsonPath('conflict.post_id', 101);
    }

    #[Test]
    public function publishing_requires_connection_approval_and_valid_schedule(): void
    {
        $article = $this->approvedArticle();
        $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'draft'])->assertStatus(503)
            ->assertExactJson(['detail' => 'wordpress_not_configured']);
        $this->getJson("/api/article-versions/{$article->id}/wordpress")->assertJsonPath('wordpress_connected', false);

        $this->connect();
        $draft = $this->makeArticle($this->makeCandidate());
        $this->postJson("/api/article-versions/{$draft->id}/wordpress", ['status' => 'draft'])->assertStatus(409)
            ->assertExactJson(['detail' => 'WordPress wymaga zatwierdzonej wersji.']);
        $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'future'])->assertStatus(422);
        $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'future', 'scheduled_at' => '2020-01-01T10:00:00+00:00'])->assertStatus(422);
        $this->postJson("/api/article-versions/{$article->id}/wordpress/sync", [])->assertStatus(409)
            ->assertExactJson(['detail' => 'Najpierw utwórz draft WordPress.']);
    }

    #[Test]
    public function settings_update_profile_and_prepare_fills_gaps(): void
    {
        $this->connect();
        $article = $this->approvedArticle();

        $this->patchJson("/api/article-versions/{$article->id}/wordpress/settings", ['category' => 'Poradniki', 'tags' => ['LLM']])
            ->assertOk()->assertJsonPath('profile.category', 'Poradniki')->assertJsonPath('profile.tags', ['LLM']);
        $this->patchJson("/api/article-versions/{$article->id}/wordpress/settings", ['canonical_url' => 'https://x'])->assertStatus(422);
        $this->patchJson("/api/article-versions/{$article->id}/wordpress/settings", ['category' => 'Zła'])->assertStatus(422);

        $job = $this->postJson("/api/article-versions/{$article->id}/wordpress/prepare")->assertStatus(202)->json('id');
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'succeeded');
        $this->assertSame($article->id, WordPressPublication::query()->first()->profile['version_id']);
        $this->assertContains('seo.prepare', array_column($this->aiRequests, 'task'));
    }

    #[Test]
    public function transient_wordpress_errors_are_retried(): void
    {
        \Illuminate\Support\Facades\Queue::fake();
        $this->connect();
        $article = $this->approvedArticle();
        $job = $this->postJson("/api/article-versions/{$article->id}/wordpress", ['status' => 'draft'])->json('id');
        $this->wp->error = 503;

        app(\Modules\Pipeline\Services\JobRunner::class)->run($job);
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'retrying')->assertJsonPath('error_code', 'wordpress_http_503');
        $this->assertSame('queued', WordPressPublication::query()->value('status'));

        app(\Modules\Pipeline\Services\JobRunner::class)->run($job);
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'succeeded');
        $this->assertSame(1, $this->wp->creates);
    }
}
