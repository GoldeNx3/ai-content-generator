<?php

namespace Modules\WordPress\Services;

use Carbon\CarbonImmutable;
use Modules\WordPress\Client\WordPressClientFactory;
use Modules\WordPress\Commands\ReplaceWordPressPostsCommand;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Queries\WordPressPostsQuery;

final class BlogMemoryService
{
    private const MAX_PAGES = 5;

    private const STALE_AFTER_MINUTES = 60;

    private const MAX_LINKS = 20;

    public function __construct(
        private readonly ConnectionService $connections,
        private readonly WordPressClientFactory $clients,
        private readonly ReplaceWordPressPostsCommand $replace,
        private readonly WordPressPostsQuery $posts,
    ) {}

    public function summary(int $workspaceId): array
    {
        $posts = $this->posts->execute($workspaceId);

        return ['count' => count($posts), 'synced_at' => $posts === [] ? null : CarbonImmutable::parse(max(array_column($posts, 'synced_at')))->toAtomString()];
    }

    public function sync(int $workspaceId): array
    {
        $connection = $this->connections->find($workspaceId);
        if ($connection === null) {
            return $this->summary($workspaceId);
        }
        $client = $this->clients->make(ConnectionConfig::fromModel($connection));
        $posts = [];
        for ($page = 1; $page <= self::MAX_PAGES; $page++) {
            $batch = $client->request('GET', 'wp/v2/posts', ['query' => ['status' => 'publish', 'per_page' => 100, 'page' => $page, '_fields' => 'id,link,title,excerpt']]);
            foreach ($batch as $post) {
                $url = (string) ($post['link'] ?? '');
                if (! in_array(strtolower((string) parse_url($url, PHP_URL_SCHEME)), ['http', 'https'], true)) {
                    continue;
                }
                $posts[] = ['post_id' => (int) $post['id'], 'url' => mb_substr($url, 0, 2048),
                    'title' => mb_substr(html_entity_decode(strip_tags((string) ($post['title']['rendered'] ?? '')), ENT_QUOTES), 0, 1000),
                    'excerpt' => mb_substr(trim(html_entity_decode(strip_tags((string) ($post['excerpt']['rendered'] ?? '')), ENT_QUOTES)), 0, 2000)];
            }
            if (count($batch) < 100) {
                break;
            }
        }
        $this->replace->execute($workspaceId, $posts);

        return $this->summary($workspaceId);
    }

    public function refreshIfStale(int $workspaceId): void
    {
        $synced = $this->summary($workspaceId)['synced_at'];
        if ($synced !== null && CarbonImmutable::parse($synced)->greaterThan(CarbonImmutable::now()->subMinutes(self::STALE_AFTER_MINUTES))) {
            return;
        }
        try {
            $this->sync($workspaceId);
        } catch (WordPressException) {
        }
    }

    public function linkCandidates(int $workspaceId, string $text): array
    {
        $stems = self::stems($text);
        $scored = [];
        foreach ($this->posts->execute($workspaceId) as $post) {
            $score = count(array_intersect($stems, self::stems($post['title'].' '.$post['excerpt'])));
            if ($score >= 2) {
                $scored[] = ['score' => $score, 'title' => $post['title'], 'url' => $post['url']];
            }
        }
        usort($scored, fn ($a, $b) => $b['score'] <=> $a['score']);

        return array_map(fn ($post) => ['title' => $post['title'], 'url' => $post['url']], array_slice($scored, 0, self::MAX_LINKS));
    }

    private static function stems(string $text): array
    {
        preg_match_all('/[\p{L}\p{N}]{4,}/u', mb_strtolower($text), $words);

        return array_values(array_unique(array_map(fn ($word) => mb_substr($word, 0, 6), $words[0])));
    }
}
