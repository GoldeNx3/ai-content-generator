<?php

namespace Modules\Candidates\Queries;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class NearestArticleQuery
{
    public function execute(int $workspaceId, array $vector): ?object
    {
        return DB::table('articles')
            ->join('candidates', 'candidates.id', '=', 'articles.candidate_id')
            ->where('candidates.workspace_id', $workspaceId)
            ->where('articles.is_current', true)
            ->whereNotNull('articles.embedding')
            ->select('articles.id', 'articles.title')
            ->selectRaw('(SELECT SUM(a * b) FROM unnest(articles.embedding, ?::real[]) AS pair(a, b)) AS similarity', [Embedding::literal($vector)])
            ->orderByRaw('similarity DESC NULLS LAST')
            ->first();
    }
}
