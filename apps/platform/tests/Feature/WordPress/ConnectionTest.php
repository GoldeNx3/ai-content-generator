<?php

namespace Tests\Feature\WordPress;

use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Modules\WordPress\Models\WordPressConnection;
use Modules\WordPress\Models\WordPressPublication;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class ConnectionTest extends TestCase
{
    use BuildsArticles, BuildsDomain;

    private const GOOD = ['editor', 'good pass 1234'];

    private string $authorizeEndpoint = 'https://wp.example/blog/wp-admin/authorize-application.php';

    protected function setUp(): void
    {
        parent::setUp();
        config(['content.wordpress.allow_private_urls' => true]);
        Http::preventStrayRequests();
        Http::fake(fn (Request $request) => $this->site($request));
        $this->signIn();
    }

    private function site(Request $request)
    {
        $path = parse_url($request->url(), PHP_URL_PATH);
        if (str_ends_with($path, '/wp-json/')) {
            return Http::response(['authentication' => ['application-passwords' => ['endpoints' => ['authorization' => $this->authorizeEndpoint]]]]);
        }
        if (($request->header('Authorization')[0] ?? '') !== 'Basic '.base64_encode(implode(':', self::GOOD))) {
            return Http::response(['code' => 'rest_not_logged_in'], 401);
        }

        return match (true) {
            str_ends_with($path, '/users/me') => Http::response(['id' => 5, 'name' => 'Ed Itor']),
            str_ends_with($path, '/wp/v2/posts') => Http::response([]),
            str_ends_with($path, '/content-engine/v1/capabilities') => Http::response(['seo_plugin' => 'rankmath', 'can_publish' => true, 'bridge_version' => '1.0.0']),
            default => Http::response(['code' => 'rest_no_route'], 404),
        };
    }

    private function manual(array $overrides = []): array
    {
        return ['site_url' => 'https://WP.example/blog/', 'username' => self::GOOD[0], 'app_password' => self::GOOD[1], ...$overrides];
    }

    #[Test]
    public function missing_connection_is_json_null_and_disconnect_clears_it(): void
    {
        $this->assertSame('null', $this->getJson('/api/wordpress/connection')->assertOk()->getContent());
        $this->postJson('/api/wordpress/connection', $this->manual())->assertOk();
        $this->deleteJson('/api/wordpress/connection')->assertSuccessful();
        $this->assertSame('null', $this->getJson('/api/wordpress/connection')->assertOk()->getContent());
    }

    #[Test]
    public function manual_connect_verifies_and_encrypts_password(): void
    {
        $this->postJson('/api/wordpress/connection', $this->manual())->assertOk()
            ->assertJsonPath('site_url', 'https://wp.example/blog')->assertJsonPath('seo_plugin', 'rankmath')
            ->assertJsonPath('wp_user_name', 'Ed Itor')->assertJsonMissingPath('app_password');
        $raw = WordPressConnection::query()->toBase()->value('app_password');
        $this->assertStringNotContainsString(self::GOOD[1], $raw);
        $this->assertSame(self::GOOD[1], WordPressConnection::query()->first()->app_password);
        $this->getJson('/api/wordpress/connection')->assertJsonPath('username', 'editor');
        $this->postJson('/api/wordpress/connection/test')->assertJsonPath('last_error', null);
        $this->patchJson('/api/wordpress/connection', ['default_status' => 'publish', 'default_author_id' => 3])->assertJsonPath('default_author_id', 3);
        $this->patchJson('/api/wordpress/connection', ['default_status' => 'nope'])->assertStatus(422);
    }

    #[Test]
    public function wrong_password_and_invalid_urls_are_rejected(): void
    {
        $this->postJson('/api/wordpress/connection', $this->manual(['app_password' => 'wrong']))
            ->assertStatus(422)->assertExactJson(['detail' => ['code' => 'wordpress_http_401']]);
        foreach (['ftp://wp.example', 'https://user:pass@wp.example', 'https://wp.example/?a=1'] as $url) {
            $this->postJson('/api/wordpress/connection', $this->manual(['site_url' => $url]))->assertStatus(422);
        }
        $this->assertSame(0, WordPressConnection::query()->count());
    }

    #[Test]
    public function authorize_endpoint_from_the_site_must_be_an_http_url_on_that_site(): void
    {
        foreach (['javascript:fetch(1)//', 'data:text/html,x', 'https://evil.example/authorize-application.php', '//evil.example/a'] as $endpoint) {
            $this->authorizeEndpoint = $endpoint;
            $this->postJson('/api/wordpress/connection/authorize', ['site_url' => 'https://wp.example/blog'])
                ->assertStatus(422)->assertJsonPath('detail.code', 'wordpress_app_passwords_unavailable');
        }
    }

    #[Test]
    public function authorize_flow_is_bound_to_workspace_and_single_use(): void
    {
        $url = $this->postJson('/api/wordpress/connection/authorize', ['site_url' => 'https://wp.example/blog'])->assertOk()->json('authorize_url');
        parse_str(parse_url($url, PHP_URL_QUERY), $params);
        $this->assertSame('Content Engine', $params['app_name']);
        parse_str(parse_url($params['success_url'], PHP_URL_QUERY), $callback);
        $this->assertStringEndsWith('/settings/wordpress/callback', parse_url($params['success_url'], PHP_URL_PATH));

        $this->postJson('/api/wordpress/connection/authorize/complete', ['state' => str_repeat('x', 40), 'user_login' => 'editor', 'password' => self::GOOD[1]])
            ->assertStatus(400)->assertExactJson(['detail' => ['code' => 'wordpress_auth_state_invalid']]);
        $this->postJson('/api/wordpress/connection/authorize/complete', ['state' => $callback['state'], 'user_login' => 'editor', 'password' => self::GOOD[1]])
            ->assertOk()->assertJsonPath('site_url', 'https://wp.example/blog');
        $this->postJson('/api/wordpress/connection/authorize/complete', ['state' => $callback['state'], 'user_login' => 'editor', 'password' => self::GOOD[1]])
            ->assertStatus(400);
    }

    #[Test]
    public function site_change_requires_confirmation_and_unlinks_publications(): void
    {
        $this->postJson('/api/wordpress/connection', $this->manual());
        $instance = WordPressConnection::query()->value('instance_id');
        $candidate = $this->makeCandidate();
        $article = $this->makeArticle($candidate);
        WordPressPublication::query()->create(['candidate_id' => $candidate->id, 'article_version_id' => $article->id,
            'wordpress_post_id' => 81, 'wordpress_instance_id' => $instance, 'status' => 'draft_created', 'wp_status' => 'draft']);

        $this->postJson('/api/wordpress/connection', $this->manual(['site_url' => 'https://other.example']))
            ->assertStatus(409)->assertExactJson(['detail' => ['code' => 'wordpress_site_change_requires_confirmation']]);
        $this->postJson('/api/wordpress/connection', $this->manual(['site_url' => 'https://other.example', 'confirm_site_change' => true]))->assertOk();
        $this->assertNull(WordPressPublication::query()->value('wordpress_post_id'));
        $this->assertNotSame($instance, WordPressConnection::query()->value('instance_id'));
    }

    #[Test]
    public function private_addresses_are_blocked(): void
    {
        config(['content.wordpress.allow_private_urls' => false]);
        $this->postJson('/api/wordpress/connection/authorize', ['site_url' => 'http://127.0.0.1:9'])
            ->assertStatus(422)->assertExactJson(['detail' => ['code' => 'wordpress_connection']]);
    }

    #[Test]
    public function connection_can_be_imported_from_env_once(): void
    {
        config(['content.wordpress.import' => ['url' => 'https://wp.example/blog', 'api_url' => null, 'username' => self::GOOD[0], 'app_password' => self::GOOD[1]]]);

        $this->artisan('wordpress:import-env', ['--workspace' => $this->workspace->id])->assertSuccessful();

        $connection = WordPressConnection::query()->where('workspace_id', $this->workspace->id)->sole();
        $this->assertSame(self::GOOD[1], $connection->app_password);
        $this->assertSame('rankmath', $connection->seo_plugin);
        $this->artisan('wordpress:import-env', ['--workspace' => $this->workspace->id])->assertFailed();
    }

    #[Test]
    public function env_import_requires_credentials_and_valid_password(): void
    {
        config(['content.wordpress.import' => ['url' => 'https://wp.example/blog', 'api_url' => null, 'username' => self::GOOD[0], 'app_password' => null]]);
        $this->artisan('wordpress:import-env')->assertFailed();

        config(['content.wordpress.import.app_password' => 'wrong']);
        $this->artisan('wordpress:import-env')->assertFailed();

        $this->assertSame(0, WordPressConnection::query()->count());
    }
}
