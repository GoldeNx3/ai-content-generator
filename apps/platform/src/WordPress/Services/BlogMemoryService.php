<?php

namespace Modules\WordPress\Services;

use Carbon\CarbonImmutable;
use Modules\WordPress\Client\WordPressClientFactory;
use Modules\WordPress\Commands\ReplaceWordPressPostsCommand;
use Modules\WordPress\Data\BlogMemoryData;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Queries\WordPressPostsQuery;
use Throwable;

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

    public function summary(int $workspaceId): BlogMemoryData
    {
        $synced = $this->connections->find($workspaceId)?->posts_synced_at;

        return new BlogMemoryData(count($this->posts->execute($workspaceId)), $synced?->toAtomString());
    }

    public function sync(int $workspaceId): BlogMemoryData
    {
        $connection = $this->connections->find($workspaceId);
        if ($connection === null) {
            $this->replace->execute($workspaceId, [], false);

            return $this->summary($workspaceId);
        }
        $client = $this->clients->make(ConnectionConfig::fromModel($connection));
        $posts = [];
        for ($page = 1; $page <= self::MAX_PAGES; $page++) {
            try {
                $batch = $client->request('GET', 'wp/v2/posts', ['query' => ['status' => 'publish', 'per_page' => 100, 'page' => $page, '_fields' => 'id,link,title,excerpt']]);
            } catch (WordPressException $exception) {
                if ($page > 1 && $exception->errorCode === 'wordpress_http_400') {
                    break;
                }
                throw $exception;
            }
            if (! array_is_list($batch)) {
                throw new WordPressException('wordpress_invalid_json');
            }
            foreach ($batch as $post) {
                $url = is_array($post) && is_scalar($post['link'] ?? null) ? (string) $post['link'] : '';
                if (! is_numeric($post['id'] ?? null) || ! in_array(strtolower((string) parse_url($url, PHP_URL_SCHEME)), ['http', 'https'], true)) {
                    continue;
                }
                $posts[(int) $post['id']] = ['post_id' => (int) $post['id'], 'url' => mb_substr($url, 0, 2048),
                    'title' => mb_substr(html_entity_decode(strip_tags((string) ($post['title']['rendered'] ?? '')), ENT_QUOTES), 0, 1000),
                    'excerpt' => mb_substr(trim(html_entity_decode(strip_tags((string) ($post['excerpt']['rendered'] ?? '')), ENT_QUOTES)), 0, 2000)];
            }
            if (count($batch) < 100) {
                break;
            }
        }
        $this->replace->execute($workspaceId, array_values($posts), true);

        return $this->summary($workspaceId);
    }

    public function blogUrl(int $workspaceId): ?string
    {
        return $this->connections->find($workspaceId)?->site_url;
    }

    public function postForRefresh(int $workspaceId, int $postId): ?array
    {
        $connection = $this->connections->find($workspaceId);
        if ($connection === null) {
            return null;
        }
        try {
            $post = $this->clients->make(ConnectionConfig::fromModel($connection))->getPost($postId);
        } catch (Throwable $exception) {
            report($exception);

            return null;
        }
        $url = is_string($post['link'] ?? null) ? $post['link'] : null;
        $content = self::text((string) ($post['content']['raw'] ?? $post['content']['rendered'] ?? ''));
        if ($url === null || $content === '') {
            return null;
        }

        return ['title' => mb_substr(self::text((string) ($post['title']['raw'] ?? $post['title']['rendered'] ?? '')), 0, 1000),
            'url' => mb_substr($url, 0, 2048), 'content' => mb_substr($content, 0, 20000)];
    }

    private static function text(string $html): string
    {
        $text = preg_replace('#<br\s*/?>|</(p|h[1-6]|li|div|blockquote|pre|tr)>#i', "\n\n", $html);
        $text = html_entity_decode(strip_tags((string) $text), ENT_QUOTES | ENT_HTML5);
        $text = preg_replace("/[ \t]+/u", ' ', $text);
        $text = preg_replace("/ *\n */u", "\n", (string) $text);

        return trim((string) preg_replace("/\n{3,}/", "\n\n", (string) $text));
    }

    public function refreshIfStale(int $workspaceId): void
    {
        $synced = $this->connections->find($workspaceId)?->posts_synced_at;
        if ($synced !== null && $synced->greaterThan(CarbonImmutable::now()->subMinutes(self::STALE_AFTER_MINUTES))) {
            return;
        }
        try {
            $this->sync($workspaceId);
        } catch (Throwable $exception) {
            report($exception);
        }
    }

    public function linkCandidates(int $workspaceId, string $text, ?int $exceptPostId = null): array
    {
        $stems = self::stems($text);
        $scored = [];
        foreach ($this->posts->execute($workspaceId) as $post) {
            if ($exceptPostId !== null && (int) $post['post_id'] === $exceptPostId) {
                continue;
            }
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
