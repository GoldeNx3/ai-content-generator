<?php

namespace Modules\Qa\Queries;

use Modules\Qa\Models\ArticleQa;

final class LatestQaQuery
{
    public function execute(int $articleId, bool $completedOnly = false): ?ArticleQa
    {
        return ArticleQa::query()
            ->where('article_id', $articleId)
            ->when($completedOnly, fn ($query) => $query->where('status', 'completed'))
            ->orderByDesc('created_at')
            ->orderByDesc('id')
            ->first();
    }
}
