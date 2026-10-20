<?php

namespace Modules\Articles\Queries;

use Modules\Articles\Models\Article;

final class FindWorkspaceArticleQuery
{
    public function execute(int $id, int $workspaceId): ?Article
    {
        return Article::query()
            ->select('articles.*')
            ->join('candidates', 'candidates.id', '=', 'articles.candidate_id')
            ->where('articles.id', $id)
            ->where('candidates.workspace_id', $workspaceId)
            ->first();
    }
}
