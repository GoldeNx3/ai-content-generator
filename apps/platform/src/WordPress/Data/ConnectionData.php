<?php

namespace Modules\WordPress\Data;

use Carbon\CarbonImmutable;
use Modules\WordPress\Models\WordPressConnection;
use Spatie\LaravelData\Data;

final class ConnectionData extends Data
{
    public function __construct(
        public string $site_url,
        public ?string $api_url,
        public string $username,
        public string $seo_plugin,
        public string $default_status,
        public ?int $default_author_id,
        public ?int $default_category_id,
        public ?int $wp_user_id,
        public ?string $wp_user_name,
        public bool $can_publish,
        public ?CarbonImmutable $last_checked_at,
        public ?string $last_error,
    ) {}

    public static function fromModel(WordPressConnection $connection): self
    {
        return new self(
            $connection->site_url, $connection->api_url, $connection->username, $connection->seo_plugin, $connection->default_status,
            $connection->default_author_id, $connection->default_category_id, $connection->wp_user_id, $connection->wp_user_name,
            $connection->can_publish, $connection->last_checked_at, $connection->last_error,
        );
    }
}
