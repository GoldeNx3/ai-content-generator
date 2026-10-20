<?php

namespace Modules\Articles\Queries;

use Modules\Articles\Models\Article;

final class ArticleLineageQuery
{
    public function execute(Article $article): array
    {
        $versions = Article::query()->where('candidate_id', $article->candidate_id)
            ->get(['id', 'parent_version_id', 'created_by'])->keyBy('id');

        return self::walk($versions->all(), $article->id);
    }

    public static function walk(array $versions, int $articleId): array
    {
        $lineage = [];
        $current = $versions[$articleId] ?? null;
        while ($current !== null && ! in_array($current->id, $lineage, true)) {
            $lineage[] = $current->id;
            if (in_array($current->created_by, ['generated', 'regenerated', 'legacy'], true)) {
                break;
            }
            $current = $current->parent_version_id ? ($versions[$current->parent_version_id] ?? null) : null;
        }

        return $lineage;
    }
}
