<?php

namespace Modules\WordPress\Commands;

use Modules\Articles\Models\Article;
use Modules\WordPress\Models\WordPressPublication;

final class FindOrCreatePublicationCommand
{
    public function execute(Article $article): WordPressPublication
    {
        return WordPressPublication::query()->firstOrCreate(['candidate_id' => $article->candidate_id], [
            'article_version_id' => $article->id, 'title' => $article->title, 'slug' => $article->slug, 'profile' => [], 'warnings' => [],
        ]);
    }
}
