<?php

namespace Modules\WordPress\Data;

use Carbon\CarbonImmutable;
use Modules\WordPress\Models\WordPressPublication;
use Spatie\LaravelData\Data;

final class PublicationData extends Data
{
    public function __construct(
        public int $id,
        public int $article_version_id,
        public int $candidate_id,
        public ?int $wordpress_post_id,
        public ?string $wordpress_url,
        public string $status,
        public ?string $wp_status,
        public string $title,
        public string $slug,
        public ?CarbonImmutable $scheduled_at,
        public ?CarbonImmutable $published_at,
        public ?CarbonImmutable $last_synced_at,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
        public ?string $last_synced_content_hash,
        public ?int $media_id,
        public array $warnings,
        public array $profile,
        public ?string $error_code,
    ) {}

    public static function fromModel(WordPressPublication $p): self
    {
        return new self(
            $p->id, $p->article_version_id, $p->candidate_id, $p->wordpress_post_id, $p->wordpress_url, $p->status, $p->wp_status,
            $p->title, $p->slug, $p->scheduled_at, $p->published_at, $p->last_synced_at, $p->created_at->toImmutable(),
            $p->updated_at->toImmutable(), $p->last_synced_content_hash, $p->media_id, $p->warnings ?? [], $p->profile ?? [], $p->error_code,
        );
    }
}
