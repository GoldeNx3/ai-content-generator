<?php

namespace Modules\WordPress\Client;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Factory as Http;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Support\PublicHostGuard;

final class WordPressClient
{
    public function __construct(
        private readonly Http $http,
        private readonly PublicHostGuard $guard,
        private readonly ConnectionConfig $config,
    ) {}

    public function config(): ConnectionConfig
    {
        return $this->config;
    }

    public function request(string $method, string $path, array $options = [], bool $auth = true): array
    {
        $base = rtrim($this->config->apiUrl ?: $this->config->siteUrl, '/');
        $url = $base.'/wp-json/'.$path;
        $request = $this->pending($url, $auth)->withHeaders($options['headers'] ?? []);
        try {
            $response = match ($method) {
                'GET' => $request->get($url, $options['query'] ?? []),
                'POST' => isset($options['body'])
                    ? $request->withBody($options['body'], $options['content_type'])->post($url)
                    : $request->post($url, $options['json'] ?? []),
            };
        } catch (ConnectionException $exception) {
            $code = str_contains(strtolower($exception->getMessage()), 'timed out') ? 'wordpress_timeout' : 'wordpress_connection';
            throw new WordPressException($code, true);
        }

        return $this->decode($response);
    }

    public function index(): array
    {
        return $this->request('GET', '', auth: false);
    }

    public function capabilities(): array
    {
        return $this->request('GET', 'content-engine/v1/capabilities');
    }

    public function testConnection(): array
    {
        $user = $this->getUser('me');
        $this->request('GET', 'wp/v2/posts', ['query' => ['context' => 'edit', 'per_page' => 1]]);

        return ['user_id' => $user['id'] ?? null, 'user_name' => $user['name'] ?? null, 'capabilities' => $this->capabilities()];
    }

    public function getUser(int|string $id): array
    {
        return $this->request('GET', "wp/v2/users/{$id}", ['query' => ['context' => 'edit']]);
    }

    public function getPost(int $id): array
    {
        return $this->request('GET', "wp/v2/posts/{$id}", ['query' => ['context' => 'edit']]);
    }

    public function createPost(array $payload, string $identity, string $operation): array
    {
        return $this->request('POST', 'content-engine/v1/posts', ['json' => ['identity' => $identity, 'operation' => $operation, 'post' => $payload]]);
    }

    public function updatePost(int $id, array $payload, string $identity, string $operation, ?string $expectedHash = null): array
    {
        return $this->request('POST', "content-engine/v1/posts/{$id}", ['json' => [
            'identity' => $identity, 'operation' => $operation, 'expected_hash' => $expectedHash, 'post' => $payload,
        ]]);
    }

    public function findTerm(string $kind, string $name): ?array
    {
        foreach ($this->request('GET', "wp/v2/{$kind}", ['query' => ['search' => $name, 'per_page' => 100]]) as $row) {
            if (mb_strtolower($row['name'] ?? '') === mb_strtolower($name)) {
                return $row;
            }
        }

        return null;
    }

    public function createTerm(string $kind, string $name): array
    {
        return $this->request('POST', "wp/v2/{$kind}", ['json' => ['name' => $name]]);
    }

    public function uploadMedia(string $data, string $filename, string $mime): array
    {
        return $this->request('POST', 'content-engine/v1/media', [
            'body' => $data, 'content_type' => $mime, 'headers' => ['Content-Disposition' => "attachment; filename=\"{$filename}\""],
        ]);
    }

    public function operation(string $key): array
    {
        return $this->request('GET', 'content-engine/v1/operation', ['query' => ['operation' => $key]]);
    }

    public function resolve(string $url): array
    {
        return $this->request('GET', 'content-engine/v1/resolve', ['query' => ['url' => $url]]);
    }

    private function pending(string $url, bool $auth): PendingRequest
    {
        $request = $this->http->timeout(config('content.wordpress.timeout_seconds'))->withoutRedirecting()->acceptJson();
        if ($auth) {
            $request = $request->withBasicAuth($this->config->username, $this->config->password);
        }
        if ($this->config->apiUrl && $this->config->apiUrl !== $this->config->siteUrl) {
            $request = $request->withHeaders(['Host' => parse_url($this->config->siteUrl, PHP_URL_HOST).(parse_url($this->config->siteUrl, PHP_URL_PORT) ? ':'.parse_url($this->config->siteUrl, PHP_URL_PORT) : '')]);
        }
        if (! config('content.wordpress.allow_private_urls')) {
            $request = $request->withOptions(['curl' => $this->guard->curlResolve($url)]);
        }

        return $request;
    }

    private function decode(Response $response): array
    {
        if ($response->status() >= 300) {
            $code = 'wordpress_http_'.$response->status();
            $details = null;
            if ($response->status() === 409) {
                $details = $response->json('data');
                if ($response->json('code') === 'ce_content_conflict') {
                    $code = 'wordpress_conflict';
                }
            }
            $retryAfter = is_numeric($response->header('Retry-After')) ? (float) $response->header('Retry-After') : null;
            throw new WordPressException($code, $response->status() === 429 || $response->status() >= 500, $retryAfter, is_array($details) ? $details : null);
        }
        $json = $response->json();
        if (! is_array($json)) {
            throw new WordPressException('wordpress_invalid_json');
        }

        return $json;
    }
}
