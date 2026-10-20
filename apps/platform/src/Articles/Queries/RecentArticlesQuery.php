<?php

namespace Modules\Articles\Queries;

use Modules\Articles\Models\Article;

final class RecentArticlesQuery
{
    public function execute(int $workspaceId, int $limit = 5): array
    {
        return Article::query()
            ->join('candidates', 'candidates.id', '=', 'articles.candidate_id')
            ->where('candidates.workspace_id', $workspaceId)
            ->where('articles.is_current', true)
            ->orderByDesc('articles.created_at')
            ->orderByDesc('articles.id')
            ->limit($limit)
            ->get(['articles.sections', 'articles.content'])
            ->map(fn (Article $article) => ['sections' => $article->sections ?? [], 'content' => $article->content])
            ->all();
    }
}
