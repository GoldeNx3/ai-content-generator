<?php

namespace Modules\WordPress\Services;

use Modules\Ai\Services\AiRunner;
use Modules\Articles\Models\Article;
use Modules\WordPress\Models\WordPressPublication;

final class ProfileService
{
    private const TIMEOUT = 60;

    public function __construct(private readonly AiRunner $ai) {}

    public function article(Article $article): array
    {
        return [
            'title' => $article->title, 'slug' => $article->slug, 'lead' => $article->lead, 'content' => $article->content,
            'meta_title' => $article->meta_title, 'meta_description' => $article->meta_description,
            'article_type' => $article->article_type->value, 'seo_data' => $article->seo_data ?? [], 'brief' => $article->brief ?? [],
            'sections' => $article->sections ?? [], 'research_snapshot' => $article->research_snapshot ?? [],
        ];
    }

    public function overrides(Article $article, ?WordPressPublication $publication): array
    {
        $profile = $publication?->profile ?? [];

        return ($profile['version_id'] ?? $article->id) === $article->id ? $profile : [];
    }

    public function stored(Article $article, ?WordPressPublication $publication): array
    {
        return [
            ...$article->seo_preview ?? [],
            'title' => $article->title, 'slug' => $article->slug, 'seo_title' => $article->meta_title,
            'meta_description' => $article->meta_description,
            ...array_diff_key($this->overrides($article, $publication), ['version_id' => true, 'category_override' => true]),
        ];
    }

    public function resolve(Article $article, array $overrides): array
    {
        return $this->ai->run('seo.profile', ['article' => $this->article($article), 'overrides' => $overrides],
            $article->candidate->isDemo(), self::TIMEOUT)->result['profile'];
    }
}
