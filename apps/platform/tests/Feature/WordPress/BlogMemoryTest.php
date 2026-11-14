<?php

namespace Tests\Feature\WordPress;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Modules\WordPress\Models\WordPressConnection;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\Support\FakeWordPress;
use Tests\TestCase;

final class BlogMemoryTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private FakeWordPress $wp;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        config(['content.wordpress.allow_private_urls' => true]);
        $this->wp = new FakeWordPress;
        $this->wp->published = [
            ['id' => 11, 'link' => 'https://wp.example/blog/kolejki-w-laravel/', 'title' => 'Kolejki w Laravel – jak je monitorować', 'excerpt' => 'Horizon i metryki.'],
            ['id' => 12, 'link' => 'https://wp.example/blog/kubernetes/', 'title' => 'Kubernetes dla początkujących', 'excerpt' => 'Pody.'],
        ];
        Http::preventStrayRequests();
        Http::fake(fn ($request) => $this->wp->handle($request));
        WordPressConnection::query()->create(['workspace_id' => $this->workspace->id, 'site_url' => 'https://wp.example/blog', 'username' => 'editor',
            'app_password' => 'secret', 'instance_id' => 'ce-test', 'seo_plugin' => 'yoast']);
    }

    #[Test]
    public function published_posts_are_remembered_per_account(): void
    {
        $this->postJson('/api/wordpress/posts/sync')->assertOk()->assertJsonPath('count', 2);

        $this->getJson('/api/wordpress/posts')->assertJsonPath('count', 2)->assertJsonStructure(['count', 'synced_at']);
        $this->assertSame('Kolejki w Laravel – jak je monitorować', DB::table('wordpress_posts')->where('post_id', 11)->value('title'));
        $this->assertSame(0, DB::table('wordpress_posts')->where('workspace_id', '!=', $this->workspace->id)->count());

        $this->wp->published = [$this->wp->published[1]];
        $this->postJson('/api/wordpress/posts/sync')->assertOk()->assertJsonPath('count', 1);
    }

    #[Test]
    public function the_writer_gets_matching_posts_as_the_only_allowed_internal_links(): void
    {
        $this->postJson('/api/wordpress/posts/sync')->assertOk();
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate(['title' => 'Laravel 13: nowe kolejki i monitorowanie']);
        $this->completedResearch($candidate);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $links = collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['internal_links'];
        $this->assertSame([['title' => 'Kolejki w Laravel – jak je monitorować', 'url' => 'https://wp.example/blog/kolejki-w-laravel/']], $links);
        $this->assertSame('https://wp.example/blog', collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['blog_url']);
    }

    #[Test]
    public function a_regenerated_article_never_links_to_its_own_published_post(): void
    {
        $this->postJson('/api/wordpress/posts/sync')->assertOk();
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate(['title' => 'Laravel 13: nowe kolejki i monitorowanie']);
        $this->completedResearch($candidate);
        DB::table('wordpress_publications')->insert(['candidate_id' => $candidate->id, 'article_version_id' => $this->makeArticle($candidate)->id,
            'wordpress_post_id' => 11, 'wordpress_instance_id' => 'ce-test', 'wordpress_url' => 'https://wp.example/blog/kolejki-w-laravel/',
            'status' => 'synced', 'created_at' => now(), 'updated_at' => now()]);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $this->assertSame([], collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['internal_links']);
    }

    #[Test]
    public function a_topic_resembling_a_blog_post_is_flagged_when_classified(): void
    {
        $this->postJson('/api/wordpress/posts/sync')->assertOk();
        $this->fakeAi(['classify' => self::aiOk(['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'])]);
        $candidate = $this->makeCandidate(['title' => 'Kolejki w Laravel - jak je monitorować']);

        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(202);

        $covered = collect($this->aiRequests)->firstWhere('task', 'classify')['input']['candidate']['already_covered'];
        $this->assertSame('Kolejki w Laravel – jak je monitorować', $covered['title']);
        $this->assertSame('https://wp.example/blog/kolejki-w-laravel/', $covered['url']);
    }

    #[Test]
    public function a_blog_with_exactly_one_full_page_of_posts_is_synced(): void
    {
        $this->wp->published = array_map(fn (int $i) => ['id' => $i, 'link' => "https://wp.example/blog/p{$i}/", 'title' => "Wpis {$i}", 'excerpt' => ''], range(1, 100));

        $this->postJson('/api/wordpress/posts/sync')->assertOk()->assertJsonPath('count', 100);
    }

    #[Test]
    public function an_empty_blog_counts_as_synced_and_is_not_fetched_before_every_article(): void
    {
        $this->wp->published = [];
        $this->postJson('/api/wordpress/posts/sync')->assertOk()->assertJsonPath('count', 0);
        $this->assertNotNull($this->getJson('/api/wordpress/posts')->json('synced_at'));
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate(['title' => 'Laravel 13']);
        $this->completedResearch($candidate);
        $listCalls = fn () => count(Http::recorded(fn ($request) => str_contains($request->url(), 'wp/v2/posts')));
        $before = $listCalls();

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $this->assertSame($before, $listCalls());
    }

    #[Test]
    public function disconnecting_or_changing_the_site_forgets_the_old_posts(): void
    {
        $this->postJson('/api/wordpress/posts/sync')->assertOk();

        $this->deleteJson('/api/wordpress/connection')->assertNoContent();

        $this->assertSame(0, DB::table('wordpress_posts')->count());
        $this->postJson('/api/wordpress/posts/sync')->assertOk()->assertJsonPath('count', 0)->assertJsonPath('synced_at', null);
    }

    #[Test]
    public function a_broken_blog_response_never_fails_the_paid_writing_step(): void
    {
        $this->wp->postsListBody = [['link' => 'https://wp.example/blog/bez-id/', 'title' => 'Kolejki w Laravel']];
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate(['title' => 'Laravel 13: nowe kolejki']);
        $this->completedResearch($candidate);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $this->assertSame([], collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['internal_links']);
    }
}
