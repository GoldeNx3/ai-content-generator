<?php

namespace Tests\Feature\Sources;

use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\Shared\Support\PublicNetwork;
use Modules\Sources\Models\Source;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class SourceUrlSafetyTest extends TestCase
{
    private const PUBLIC_FEED = 'http://93.184.216.34/feed.xml';

    protected function setUp(): void
    {
        parent::setUp();
        config(['content.sources.allow_private_urls' => false, 'content.ingestion.fetch_max_age_days' => 0]);
        Http::preventStrayRequests();
        $this->signIn();
    }

    public static function nonPublicAddresses(): array
    {
        return array_map(fn (string $ip) => [$ip], [
            '127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.1.1', '169.254.169.254', '0.0.0.0', '100.64.0.1',
            '198.18.0.1', '192.0.0.8', '224.0.0.1', '::1', 'fc00::1', 'fe80::1', '::ffff:127.0.0.1', '64:ff9b::7f00:1',
        ]);
    }

    #[Test]
    #[DataProvider('nonPublicAddresses')]
    public function non_public_addresses_are_rejected(string $ip): void
    {
        $this->assertFalse(PublicNetwork::isPublicIp($ip), "{$ip} must not be public");
    }

    #[Test]
    public function public_addresses_are_accepted(): void
    {
        foreach (['93.184.216.34', '8.8.8.8', '2606:2800:220:1:248:1893:25c8:1946'] as $ip) {
            $this->assertTrue(PublicNetwork::isPublicIp($ip), "{$ip} must be public");
        }
    }

    #[Test]
    public function curl_resolve_entry_brackets_ipv6(): void
    {
        $this->assertSame('feed.test:443:93.184.216.34,[2606:2800:220:1:248:1893:25c8:1946]',
            PublicNetwork::curlResolveEntry('feed.test', 443, ['93.184.216.34', '2606:2800:220:1:248:1893:25c8:1946']));
    }

    #[Test]
    public function sources_pointing_at_internal_hosts_are_rejected(): void
    {
        foreach (['http://127.0.0.1:6379/', 'http://169.254.169.254/latest/meta-data/', 'http://localhost/feed', 'http://[::1]/feed',
            'http://user:pass@93.184.216.34/feed.xml'] as $url) {
            $this->postJson('/api/sources', ['name' => 'X', 'url' => $url])->assertStatus(422);
        }
        $source = Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'Ok', 'url' => self::PUBLIC_FEED]);
        $this->patchJson("/api/sources/{$source->id}", ['url' => 'http://10.0.0.5/feed'])->assertStatus(422);
        $this->assertSame(0, Source::query()->where('url', 'like', '%127.0.0.1%')->count());
    }

    #[Test]
    public function redirect_to_an_internal_host_is_not_followed(): void
    {
        Http::fake([self::PUBLIC_FEED => Http::response('', 302, ['Location' => 'http://127.0.0.1:6379/'])]);
        $source = Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'Ok', 'url' => self::PUBLIC_FEED]);

        $this->postJson("/api/sources/{$source->id}/fetch")->assertOk()->assertJsonPath('errors', 1);

        Http::assertSentCount(1);
    }

    #[Test]
    public function public_redirects_are_followed_a_few_times(): void
    {
        Http::fake([
            self::PUBLIC_FEED => Http::response('', 301, ['Location' => 'http://93.184.216.35/moved.xml']),
            'http://93.184.216.35/moved.xml' => Http::response(file_get_contents(base_path('tests/Fixtures/rss.xml'))),
        ]);
        $source = Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'Ok', 'url' => self::PUBLIC_FEED]);

        $this->postJson("/api/sources/{$source->id}/fetch")->assertOk()->assertJsonPath('errors', 0);
        $this->assertGreaterThan(0, Candidate::query()->count());
    }

    #[Test]
    public function oversized_feed_is_rejected(): void
    {
        $xml = '<?xml version="1.0"?><rss version="2.0"><channel><title>T</title><item><title>Duży</title><link>https://example.com/big</link><description>'
            .str_repeat('a', 5 * 1024 * 1024).'</description></item></channel></rss>';
        Http::fake([self::PUBLIC_FEED => Http::response($xml)]);
        $source = Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'Ok', 'url' => self::PUBLIC_FEED]);

        $this->postJson("/api/sources/{$source->id}/fetch")->assertOk()->assertJsonPath('errors', 1);
    }

    #[Test]
    public function feed_items_with_unsafe_or_overlong_links_are_skipped(): void
    {
        $long = 'https://example.com/'.str_repeat('a', 2100);
        $xml = '<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
            .'<item><title>Zły</title><link>javascript:alert(1)</link></item>'
            .'<item><title>Długi</title><link>'.$long.'</link></item>'
            .'<item><title>Dobry</title><link>https://example.com/ok</link></item>'
            .'</channel></rss>';
        Http::fake([self::PUBLIC_FEED => Http::response($xml)]);
        $source = Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'Ok', 'url' => self::PUBLIC_FEED]);

        $this->postJson("/api/sources/{$source->id}/fetch")->assertOk()->assertJsonPath('errors', 0)->assertJsonPath('new_candidates', 1);
        $this->assertSame(['https://example.com/ok'], Candidate::query()->pluck('external_url')->all());
    }
}
