<?php

namespace Modules\Articles\Queries;

use Illuminate\Support\Collection;
use Modules\Articles\Models\Article;

final class ArticleVersionsQuery
{
    public function execute(int $candidateId): Collection
    {
        return Article::query()->where('candidate_id', $candidateId)->orderByDesc('version')->get();
    }
}
