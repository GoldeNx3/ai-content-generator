<?php

namespace Modules\Candidates\Queries;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class NearestArticleQuery
{
    public function execute(int $workspaceId, array $vector, ?string $model): ?object
    {
        return DB::table('articles')
            ->join('candidates', 'candidates.id', '=', 'articles.candidate_id')
            ->where('candidates.workspace_id', $workspaceId)
            ->where('articles.is_current', true)
            ->whereNotNull('articles.embedding')
            ->where('articles.embedding_model', $model)
            ->whereRaw('cardinality(articles.embedding) = ?', [count($vector)])
            ->leftJoin('wordpress_publications as publication', 'publication.candidate_id', '=', 'articles.candidate_id')
            ->select('articles.id', 'articles.title', 'publication.wordpress_post_id', 'publication.wordpress_url')
            ->selectRaw('(SELECT SUM(a * b) FROM unnest(articles.embedding, ?::real[]) AS pair(a, b)) AS similarity', [Embedding::literal($vector)])
            ->orderByRaw('similarity DESC NULLS LAST')
            ->first();
    }
}
