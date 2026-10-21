<?php

namespace Modules\WordPress\Commands;

use Modules\Articles\Models\Article;
use Modules\WordPress\Models\WordPressPublication;

final class PublicationCommand
{
    public function forArticle(Article $article, array $defaultProfile = []): WordPressPublication
    {
        return WordPressPublication::query()->firstOrCreate(['candidate_id' => $article->candidate_id], [
            'article_version_id' => $article->id, 'title' => $article->title, 'slug' => $article->slug,
            'profile' => $defaultProfile, 'warnings' => [],
        ]);
    }

    public function update(WordPressPublication $publication, array $attributes): void
    {
        $publication->forceFill($attributes)->save();
    }
}
