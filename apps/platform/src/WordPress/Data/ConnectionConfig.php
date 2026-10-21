<?php

namespace Modules\WordPress\Data;

use Modules\WordPress\Models\WordPressConnection;

final readonly class ConnectionConfig
{
    public function __construct(
        public string $siteUrl,
        public ?string $apiUrl,
        public string $username,
        public string $password,
        public string $instanceId = '',
        public string $seoPlugin = 'none',
        public ?int $defaultAuthorId = null,
        public ?int $defaultCategoryId = null,
    ) {}

    public static function fromModel(WordPressConnection $connection): self
    {
        return new self(
            $connection->site_url, $connection->api_url, $connection->username, $connection->app_password,
            $connection->instance_id, $connection->seo_plugin, $connection->default_author_id, $connection->default_category_id,
        );
    }
}
