<?php

namespace Tests\Feature\Sources;

use Illuminate\Support\Facades\Http;
use Modules\Candidates\Models\Candidate;
use Modules\Sources\Models\Source;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class UrlDeduplicationTest extends TestCase
{
    private function feed(array $links): string
    {
        $items = implode('', array_map(fn (string $link, int $i) => "<item><title>Wpis {$i}</title><link>".htmlspecialchars($link).'</link></item>', $links, array_keys($links)));

        return '<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'.$items.'</channel></rss>';
    }

    #[Test]
    public function the_same_article_behind_tracking_parameters_or_www_is_saved_once(): void
    {
        $this->signIn();
        config(['content.ingestion.fetch_max_age_days' => 0]);
        Http::preventStrayRequests();
        Http::fake([
            'https://a.example/feed.xml' => Http::response($this->feed(['https://news.example/post/1?utm_source=rss', 'https://news.example/post/2'])),
            'https://b.example/feed.xml' => Http::response($this->feed(['https://www.news.example/post/1/', 'http://news.example/post/2?fbclid=x'])),
        ]);
        foreach (['https://a.example/feed.xml', 'https://b.example/feed.xml'] as $url) {
            Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => $url, 'url' => $url]);
        }

        $this->postJson('/api/sources/fetch')->assertOk()->assertJsonPath('new_candidates', 2);

        $this->assertSame(['https://news.example/post/1?utm_source=rss', 'https://news.example/post/2'], Candidate::query()->orderBy('id')->pluck('external_url')->all());
    }
}
