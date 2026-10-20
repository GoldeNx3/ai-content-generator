<?php

namespace Modules\Articles\Commands;

use Modules\Articles\Models\Article;
use Modules\Articles\Support\ContentHash;

final class CreateArticleVersionCommand
{
    public function execute(int $candidateId, int $version, array $attributes): Article
    {
        Article::query()->where('candidate_id', $candidateId)->where('is_current', true)->update(['is_current' => false]);

        return Article::query()->create([
            ...$attributes,
            'candidate_id' => $candidateId,
            'version' => $version,
            'is_current' => true,
            'content_hash' => ContentHash::of($attributes),
        ]);
    }
}
