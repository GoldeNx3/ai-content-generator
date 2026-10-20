<?php

namespace Modules\AutoFix\Queries;

use Modules\AutoFix\Models\ArticleFix;

final class FindWorkspaceFixQuery
{
    public function execute(int $id, int $workspaceId): ?ArticleFix
    {
        return ArticleFix::query()
            ->select('article_fixes.*')
            ->join('articles', 'articles.id', '=', 'article_fixes.source_article_version_id')
            ->join('candidates', 'candidates.id', '=', 'articles.candidate_id')
            ->where('article_fixes.id', $id)
            ->where('candidates.workspace_id', $workspaceId)
            ->first();
    }
}
