<?php

namespace Modules\WordPress\Services;

use Carbon\CarbonImmutable;
use Illuminate\Http\Client\Factory as Http;
use Modules\Articles\Models\Article;
use Modules\Candidates\Enums\CandidateStatus;
use Modules\Candidates\Commands\UpdateCandidateStatusCommand;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\WordPress\Client\WordPressClient;
use Modules\WordPress\Commands\FindOrCreatePublicationCommand;
use Modules\WordPress\Commands\UpdatePublicationCommand;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Models\WordPressConnection;
use Modules\WordPress\Models\WordPressPublication;
use Modules\WordPress\Support\PublicationGate;
use Modules\WordPress\Support\PublicHostGuard;
use Modules\WordPress\Support\Readiness;
use Modules\WordPress\Support\WpContentHash;

final class PublisherService
{
    private const STATUS_MAP = ['draft' => 'draft_created', 'future' => 'scheduled', 'publish' => 'published'];

    private const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

    public function __construct(
        private readonly PublicationGate $gate,
        private readonly ProfileService $profiles,
        private readonly FindOrCreatePublicationCommand $findOrCreatePublication,
        private readonly UpdatePublicationCommand $updatePublication,
        private readonly UpdateCandidateStatusCommand $updateCandidateStatus,
        private readonly Http $http,
        private readonly PublicHostGuard $guard,
    ) {}

    public function profile(JobRunContext $context, Article $article, WordPressPublication $publication, bool $forcePrepare): array
    {
        $overrides = [...($article->seo_preview ?? []), ...$this->profiles->overrides($article, $publication)];
        $profile = $context->ai('profile', 'seo.profile', ['article' => $this->profiles->article($article), 'overrides' => $overrides])['result']['profile'];
        $missing = array_filter(['seo_title', 'meta_description', 'slug', 'excerpt', 'og_title', 'og_description'], fn ($key) => empty($profile[$key]));
        if ($forcePrepare || $missing !== []) {
            $context->stage('preparing_seo');
            $profile = $context->ai('prepare', 'seo.prepare', ['article' => $this->profiles->article($article), 'overrides' => $profile])['result']['profile'];
            $context->transaction(fn () => $this->updatePublication->execute($publication, ['profile' => [...$profile, 'version_id' => $article->id]]));
        }

        return $profile;
    }

    public function publish(PipelineJob $job, JobRunContext $context, WordPressClient $client, WordPressConnection $connection,
        Article $article, WordPressPublication $p, array $profile): StageResult
    {
        $options = $job->payload['options'];
        $target = $options['status'] ?? 'draft';
        $scheduledAt = isset($options['scheduled_at']) ? CarbonImmutable::parse($options['scheduled_at']) : null;
        foreach (['title', 'slug', 'seo_title', 'meta_description'] as $key) {
            if (empty($profile[$key])) {
                throw new JobInputException("Brak wymaganego pola {$key}. Przygotuj SEO przed wysłaniem.", 422);
            }
        }
        if (trim($article->content) === '') {
            throw new JobInputException('Brak treści.', 422);
        }
        $context->stage('publishing_wordpress');
        $context->transaction(fn () => $this->updatePublication->execute($p, ['status' => 'sending', 'warnings' => [], 'error_code' => null]));

        $caps = $client->capabilities();
        if (($caps['seo_plugin'] ?? 'none') !== $connection->seo_plugin) {
            throw new WordPressException('wordpress_seo_plugin_mismatch');
        }
        if (empty($caps['bridge_version'])) {
            throw new WordPressException('wordpress_bridge_required');
        }
        if (in_array($target, ['future', 'publish'], true) && ! ($caps['can_publish'] ?? true)) {
            throw new WordPressException('wordpress_publish_forbidden');
        }
        [$categories, $tags] = $this->taxonomy($client, $connection, $profile);
        $mediaId = $this->media($context, $client, $p, $profile);
        $author = $profile['author_id'] ?? $connection->default_author_id ?? ($caps['author_id'] ?? null);
        if ($author) {
            $client->getUser((int) $author);
        }
        $warnings = [];
        $profile['verified_internal_links'] = $this->internalLinks($client, $connection, $profile, $warnings);

        $prepared = $context->checkpointValue('wp_payload');
        if ($prepared !== null) {
            ['payload' => $payload, 'profile' => $profile, 'media_id' => $mediaId] = $prepared;
        } else {
            $rendered = $context->ai('render', 'wordpress.render', ['article' => $this->profiles->article($article), 'profile' => $profile])['result'];
            $profile['slug'] = $rendered['slug'];
            $payload = ['title' => $article->title, 'slug' => $profile['slug'], 'content' => $rendered['html'], 'excerpt' => $profile['excerpt'] ?? '',
                'categories' => $categories, 'tags' => $tags];
            if ($author) {
                $payload['author'] = (int) $author;
            }
            if ($mediaId) {
                $payload['featured_media'] = $mediaId;
            }
            $context->checkpoint('wp_payload', ['payload' => $payload, 'profile' => $profile, 'media_id' => $mediaId]);
        }
        $identity = "{$connection->instance_id}:{$article->candidate_id}";
        $operation = $job->id;
        $original = $context->checkpointValue('wp_original');
        $current = null;

        if ($p->wordpress_post_id && $p->wordpress_instance_id !== $connection->instance_id) {
            $this->unlink($context, $p);
            $original = null;
        }
        if ($p->wordpress_post_id) {
            try {
                $current = $client->getPost($p->wordpress_post_id);
            } catch (WordPressException $exception) {
                if ($exception->errorCode !== 'wordpress_http_404') {
                    throw $exception;
                }
                $this->unlink($context, $p);
                $original = null;
            }
        }
        if ($current !== null && ($current['status'] ?? null) === 'trash') {
            $this->unlink($context, $p);
            $current = $original = null;
        }
        if ($current !== null) {
            $digest = WpContentHash::ofPost($current);
            $expected = $original['expected_hash'] ?? ($options['expected_wp_hash'] ?? $p->last_synced_content_hash);
            $allowed = array_filter([$expected, $original ? WpContentHash::ofText($payload['content']) : null]);
            if ($expected && ! in_array($digest, $allowed, true)) {
                $context->transaction(fn () => $this->updatePublication->execute($p, ['conflict' => ['current_hash' => $digest, 'post_id' => $p->wordpress_post_id], 'error_code' => 'wordpress_conflict']));
                throw new WordPressException('wordpress_conflict');
            }
            if ($original === null) {
                $original = ['expected_hash' => $digest, 'post_id' => $p->wordpress_post_id];
                $context->checkpoint('wp_original', $original);
            }
        }

        $context->transaction(fn () => $this->gate->approved($article, lock: true));
        if (! $p->wordpress_post_id) {
            try {
                $current = $client->createPost([...$payload, 'status' => 'draft'], $identity, $operation.':create');
            } catch (WordPressException $exception) {
                if ($exception->errorCode === 'wordpress_conflict' && is_int($exception->details['post_id'] ?? null)) {
                    $remote = $client->getPost($exception->details['post_id']);
                    $context->transaction(fn () => $this->updatePublication->execute($p, [
                        'wordpress_post_id' => $remote['id'], 'wp_status' => $remote['status'], 'wordpress_instance_id' => $connection->instance_id,
                        'wordpress_url' => $remote['ce_permalink'] ?? $remote['link'] ?? null,
                        'conflict' => ['current_hash' => WpContentHash::ofPost($remote), 'post_id' => $remote['id']], 'error_code' => 'wordpress_conflict',
                    ]));
                }
                throw $exception;
            }
            $context->transaction(fn () => $this->updatePublication->execute($p, [
                'wordpress_post_id' => $current['id'], 'wp_status' => $current['status'], 'wordpress_instance_id' => $connection->instance_id,
                'wordpress_url' => $current['ce_permalink'] ?? $current['link'] ?? null, 'last_synced_at' => null,
            ]));
            $context->checkpoint('wp_created', $current['id']);
        } else {
            $current = $client->updatePost($p->wordpress_post_id, $payload, $identity, $operation.':content', $original['expected_hash'] ?? null);
            $context->checkpoint('wp_content_written', true);
        }

        $profile['slug'] = $current['slug'] ?? $profile['slug'];
        $profile['canonical_url'] = $current['ce_permalink'] ?? $current['link'] ?? null;
        if (! $profile['canonical_url']) {
            throw new WordPressException('wordpress_permalink_missing');
        }
        $meta = $context->ai('metadata', 'wordpress.metadata', ['profile' => $profile, 'capabilities' => $caps, 'seo_plugin' => $connection->seo_plugin])['result'];
        $warnings = [...$warnings, ...$meta['warnings']];
        $expected = WpContentHash::ofPost($current);
        $context->transaction(fn () => $this->gate->approved($article, lock: true));
        $client->updatePost($p->wordpress_post_id, ['meta' => $meta['metadata']], $identity, $operation.':seo', $expected);
        $context->transaction(fn () => $this->updatePublication->execute($p, ['profile' => [...$profile, 'version_id' => $article->id], 'wordpress_url' => $profile['canonical_url']]));
        $context->checkpoint('wp_seo_written', true);

        $verify = $client->getPost($p->wordpress_post_id);
        $this->verify($verify, $payload, $profile, $mediaId);
        $warnings = [...$warnings, ...$context->ai('verify_meta', 'wordpress.verify_meta', ['metadata' => $meta['metadata'], 'post' => $verify, 'seo_plugin' => $connection->seo_plugin])['result']['warnings']];

        $context->transaction(fn () => $this->gate->approved($article, lock: true));
        $effective = $target;
        $final = ['status' => $target];
        if ($target === 'future' && $scheduledAt !== null && $scheduledAt->lessThanOrEqualTo(CarbonImmutable::now())) {
            if (! ($client->operation($operation.':status')['exists'] ?? false)) {
                throw new WordPressException('wordpress_schedule_elapsed');
            }
            $remote = $client->getPost($p->wordpress_post_id);
            if (! in_array($remote['status'] ?? null, ['future', 'publish'], true)) {
                throw new WordPressException('wordpress_schedule_changed');
            }
            $effective = $remote['status'];
            $final = null;
        }
        if ($target === 'future' && $final !== null) {
            $final['date_gmt'] = $scheduledAt->utc()->format('Y-m-d\TH:i:s');
        }
        if ($final !== null) {
            $client->updatePost($p->wordpress_post_id, $final, $identity, $operation.':status', WpContentHash::ofPost($verify));
        }
        $context->checkpoint('wp_status_sent', true);
        $verify = $client->getPost($p->wordpress_post_id);
        $this->verify($verify, $payload, $profile, $mediaId, $effective);

        $result = null;
        $context->finish(function () use ($p, $article, $profile, $verify, $effective, $scheduledAt, $warnings, &$result): StageResult {
            $this->updatePublication->execute($p, [
                'article_version_id' => $article->id, 'title' => $article->title, 'slug' => $profile['slug'], 'wp_status' => $verify['status'],
                'status' => self::STATUS_MAP[$effective], 'scheduled_at' => $scheduledAt,
                'published_at' => $effective === 'publish' ? CarbonImmutable::now() : null, 'last_synced_at' => CarbonImmutable::now(),
                'last_synced_content_hash' => WpContentHash::ofPost($verify), 'error_code' => null, 'conflict' => null,
                'warnings' => array_values(array_unique([...($p->warnings ?? []), ...$warnings])),
            ]);
            $this->updateCandidateStatus->execute($article->candidate, CandidateStatus::Approved);

            return new StageResult('wordpress_publication', $p->id);
        });

        return new StageResult('wordpress_publication', $p->id);
    }

    private function unlink(JobRunContext $context, WordPressPublication $p): void
    {
        $context->transaction(fn () => $this->updatePublication->execute($p, [
            'wordpress_post_id' => null, 'wordpress_instance_id' => null, 'last_synced_content_hash' => null, 'conflict' => null,
        ]));
        $context->checkpoint('wp_original', null);
    }

    private function taxonomy(WordPressClient $client, WordPressConnection $connection, array $profile): array
    {
        $category = $profile['category'] ?? null;
        if (! in_array($category, Readiness::CATEGORIES, true)) {
            throw new JobInputException('Kategoria nie należy do dozwolonej listy.', 422);
        }
        $categoryId = $connection->default_category_id && empty($profile['category_override'])
            ? $connection->default_category_id
            : $this->term($client, 'categories', $category);
        $tags = array_map(fn (string $name) => $this->term($client, 'tags', $name), $profile['tags'] ?? []);

        return [[$categoryId], $tags];
    }

    private function term(WordPressClient $client, string $kind, string $name): int
    {
        $term = $client->findTerm($kind, $name);
        if ($term === null) {
            try {
                $term = $client->createTerm($kind, $name);
            } catch (WordPressException $exception) {
                $term = $exception->errorCode === 'wordpress_http_400' ? $client->findTerm($kind, $name) : null;
                if ($term === null) {
                    throw $exception;
                }
            }
        }

        return (int) $term['id'];
    }

    private function media(JobRunContext $context, WordPressClient $client, WordPressPublication $p, array $profile): ?int
    {
        $image = $profile['featured_image_url'] ?? $profile['featured_image_asset'] ?? null;
        if (! $image) {
            return $p->media_id;
        }
        $fingerprint = hash('sha256', $image);
        if ($p->media_id && $p->media_fingerprint === $fingerprint) {
            return $p->media_id;
        }
        $limit = config('content.wordpress.max_image_bytes');
        if (! empty($profile['featured_image_asset'])) {
            $root = realpath(config('content.wordpress.asset_root')) ?: '';
            $path = realpath($root.'/'.$image);
            if ($root === '' || $path === false || ! str_starts_with($path, $root.DIRECTORY_SEPARATOR) || ! is_file($path)) {
                throw new JobInputException('Nieprawidłowy lokalny asset obrazka.', 422);
            }
            $data = (string) file_get_contents($path);
            $mime = mime_content_type($path) ?: '';
            $filename = basename($path);
        } else {
            $response = $this->http->timeout(20)->withoutRedirecting()
                ->withOptions(['curl' => $this->guard->curlResolve($image)])->get($image);
            if (! $response->successful()) {
                throw new JobInputException('Nie udało się pobrać obrazka.', 422);
            }
            $data = $response->body();
            $mime = strtok((string) $response->header('Content-Type'), ';') ?: '';
            $filename = 'featured.'.(explode('/', $mime)[1] ?? 'img');
        }
        if (! in_array($mime, self::IMAGE_TYPES, true) || strlen($data) > $limit) {
            throw new JobInputException('Nieobsługiwany format lub rozmiar obrazka.', 422);
        }
        $media = $client->uploadMedia($data, $filename, $mime);
        $context->transaction(fn () => $this->updatePublication->execute($p, ['media_id' => $media['id'], 'media_fingerprint' => $fingerprint]));
        $context->checkpoint('wp_media', $media['id']);

        return (int) $media['id'];
    }

    private function internalLinks(WordPressClient $client, WordPressConnection $connection, array $profile, array &$warnings): array
    {
        $verified = [];
        $siteHost = parse_url($connection->site_url, PHP_URL_HOST);
        foreach ($profile['internal_links'] ?? [] as $link) {
            $url = $link['url'] ?? '';
            if (parse_url($url, PHP_URL_HOST) !== $siteHost) {
                $warnings[] = 'Internal link pominięty: URL nie należy do WordPressa.';

                continue;
            }
            if ($client->resolve($url)['exists'] ?? false) {
                $verified[] = $link;
            } else {
                $warnings[] = "Internal link pominięty: {$url}";
            }
        }

        return $verified;
    }

    private function verify(array $post, array $payload, array $profile, ?int $mediaId, ?string $status = null): void
    {
        $title = html_entity_decode($post['title']['raw'] ?? $post['title']['rendered'] ?? '', ENT_QUOTES | ENT_HTML5);
        $sameSet = fn (string $key) => collect($post[$key] ?? [])->sort()->values()->all() === collect($payload[$key])->sort()->values()->all();
        $ok = WpContentHash::ofPost($post) === WpContentHash::ofText($payload['content'])
            && $sameSet('categories') && $sameSet('tags')
            && (empty($payload['author']) || ($post['author'] ?? null) === $payload['author'])
            && $title === $payload['title']
            && ($post['slug'] ?? null) === $profile['slug']
            && ($status === null || ($post['status'] ?? null) === $status)
            && (! $mediaId || ($post['featured_media'] ?? null) === $mediaId);
        if (! $ok) {
            throw new WordPressException('wordpress_verification_failed');
        }
    }
}
