<?php

namespace Modules\WordPress\Support;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;

final class Readiness
{
    public const CATEGORIES = ['AI', 'Modele AI', 'Programowanie', 'Narzędzia AI', 'Automatyzacja', 'Biznes', 'Newsy', 'Poradniki', 'Porównania'];

    public static function checks(Article $article, array $profile, bool $qaOk): array
    {
        $checks = [];
        foreach (['title', 'slug', 'seo_title', 'meta_description', 'excerpt'] as $key) {
            $checks[] = ['name' => $key, 'status' => ! empty($profile[$key]) ? 'ok' : 'missing'];
        }
        $checks[] = ['name' => 'content', 'status' => trim($article->content) !== '' ? 'ok' : 'missing'];
        $checks[] = ['name' => 'approved', 'status' => $article->status === ArticleStatus::Approved ? 'ok' : 'blocked'];
        $checks[] = ['name' => 'current_qa', 'status' => $qaOk ? 'ok' : 'blocked'];
        $checks[] = ['name' => 'canonical', 'status' => ! empty($profile['canonical_url']) ? 'ok' : 'pending'];
        $checks[] = ['name' => 'category', 'status' => in_array($profile['category'] ?? null, self::CATEGORIES, true) ? 'ok' : 'blocked', 'value' => $profile['category'] ?? null];
        $checks[] = ['name' => 'tags', 'status' => 'ok', 'value' => count($profile['tags'] ?? [])];
        $checks[] = ['name' => 'featured_image', 'status' => ! empty($profile['featured_image_url']) || ! empty($profile['featured_image_asset']) ? 'ok' : 'optional_missing'];
        $checks[] = ['name' => 'schema', 'status' => 'ok', 'value' => $profile['schema_type'] ?? 'Article'];
        foreach ([['seo_title', 50, 60], ['meta_description', 140, 160]] as [$key, $low, $high]) {
            $length = mb_strlen((string) ($profile[$key] ?? ''));
            $checks[] = ['name' => $key.'_length', 'status' => $length >= $low && $length <= $high ? 'ok' : 'warning', 'value' => $length];
        }

        return $checks;
    }
}
