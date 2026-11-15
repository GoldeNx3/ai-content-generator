<?php

namespace Tests\Support;

use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;

final class FakeWordPress
{
    public array $posts = [];

    public array $operations = [];

    public array $terms = ['categories' => [], 'tags' => []];

    public int $creates = 0;

    public int $nextId = 100;

    public ?int $error = null;

    public array $published = [];

    public ?array $postsListBody = null;

    public array $metaKeys = ['_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_canonical'];

    public function handle(Request $request)
    {
        $path = parse_url($request->url(), PHP_URL_PATH);
        $data = $request->data();
        if ($this->error !== null) {
            $status = $this->error;
            $this->error = null;

            return Http::response(['code' => 'error'], $status);
        }
        if (str_ends_with($path, '/capabilities')) {
            return Http::response(['bridge_version' => '1.0.0', 'seo_plugin' => 'yoast', 'meta_keys' => $this->metaKeys, 'can_publish' => true, 'author_id' => 1]);
        }
        if (str_contains($path, '/wp/v2/users/')) {
            return Http::response(['id' => 1, 'name' => 'Author']);
        }
        foreach (['categories', 'tags'] as $kind) {
            if (str_ends_with($path, "/wp/v2/{$kind}")) {
                if ($request->method() === 'GET') {
                    parse_str((string) parse_url($request->url(), PHP_URL_QUERY), $query);

                    return Http::response(array_values(array_filter($this->terms[$kind], fn ($t) => $t['name'] === ($query['search'] ?? null))));
                }
                $term = ['id' => count($this->terms[$kind]) + 1, 'name' => $data['name']];
                $this->terms[$kind][$term['id']] = $term;

                return Http::response($term, 201);
            }
        }
        if (str_contains($path, '/content-engine/v1/posts')) {
            $op = $data['operation'];
            if (isset($this->operations[$op])) {
                return Http::response($this->operations[$op]);
            }
            $payload = $data['post'];
            $tail = basename($path);
            if ($tail === 'posts') {
                $this->creates++;
                $id = ++$this->nextId;
                $this->posts[$id] = ['id' => $id, 'title' => ['raw' => ''], 'content' => ['raw' => ''], 'status' => 'draft', 'featured_media' => 0,
                    'meta' => [], 'link' => "https://wp.example/blog/?p={$id}", 'slug' => '', 'categories' => [], 'tags' => [], 'author' => 1];
            } else {
                $id = (int) $tail;
                if (! isset($this->posts[$id])) {
                    return Http::response(['code' => 'ce_missing'], 404);
                }
                if (! empty($data['expected_hash']) && $data['expected_hash'] !== hash('sha256', $this->posts[$id]['content']['raw'])) {
                    return Http::response(['code' => 'ce_content_conflict', 'data' => ['current_hash' => hash('sha256', $this->posts[$id]['content']['raw']), 'post_id' => $id]], 409);
                }
            }
            foreach ($payload as $key => $value) {
                match ($key) {
                    'title', 'content' => $this->posts[$id][$key] = ['raw' => $value, 'rendered' => $value],
                    'meta' => $this->posts[$id]['meta'] = [...$this->posts[$id]['meta'], ...$value],
                    'date_gmt' => null,
                    default => $this->posts[$id][$key] = $value,
                };
            }
            $this->posts[$id]['ce_permalink'] = 'https://wp.example/blog/'.$this->posts[$id]['slug'];

            return Http::response($this->operations[$op] = $this->posts[$id]);
        }
        if (str_contains($path, '/content-engine/v1/operation')) {
            return Http::response(['exists' => false]);
        }
        if (str_ends_with($path, '/wp/v2/posts') && $request->method() === 'GET') {
            parse_str((string) parse_url($request->url(), PHP_URL_QUERY), $query);
            $page = (int) ($query['page'] ?? 1);
            if ($this->postsListBody !== null) {
                return Http::response($this->postsListBody);
            }
            if ($page > 1 && ($page - 1) * 100 >= count($this->published)) {
                return Http::response(['code' => 'rest_post_invalid_page_number'], 400);
            }
            $chunk = array_slice($this->published, ($page - 1) * 100, 100);

            return Http::response(array_map(fn (array $post) => ['id' => $post['id'], 'link' => $post['link'], 'title' => ['rendered' => $post['title']],
                'excerpt' => ['rendered' => '<p>'.($post['excerpt'] ?? '').'</p>']], $chunk), 200, ['X-WP-TotalPages' => (string) max(1, (int) ceil(count($this->published) / 100))]);
        }
        if (preg_match('#/wp/v2/posts/(\d+)$#', $path, $match)) {
            $id = (int) $match[1];
            if (isset($this->posts[$id])) {
                return Http::response($this->posts[$id]);
            }
            $published = collect($this->published)->firstWhere('id', $id);

            return $published === null ? Http::response(['code' => 'rest_post_invalid_id'], 404) : Http::response(['id' => $id, 'link' => $published['link'],
                'title' => ['raw' => $published['title'], 'rendered' => $published['title']],
                'content' => ['raw' => $published['content'] ?? '', 'rendered' => $published['content'] ?? '']]);
        }

        return Http::response(['code' => 'rest_no_route'], 404);
    }
}
