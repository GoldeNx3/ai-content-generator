<?php

namespace Modules\Qa\Queries;

use Modules\Qa\Models\ArticleQa;

final class LatestQaForArticlesQuery
{
    public function execute(array $articleIds): array
    {
        return ArticleQa::query()
            ->whereIn('article_id', $articleIds)
            ->orderBy('article_id')
            ->orderByDesc('created_at')
            ->orderByDesc('id')
            ->get()
            ->unique('article_id')
            ->keyBy('article_id')
            ->all();
    }
}
