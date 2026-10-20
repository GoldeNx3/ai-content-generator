<?php

namespace Modules\Articles\Queries;

use Illuminate\Support\Facades\DB;

final class CompletedFixIterationsQuery
{
    public function execute(array $articleIds): array
    {
        if ($articleIds === []) {
            return [];
        }

        return DB::table('article_fixes')
            ->whereIn('source_article_version_id', $articleIds)
            ->where('status', 'completed')
            ->groupBy('source_article_version_id')
            ->selectRaw('source_article_version_id, MAX(iteration) AS iteration')
            ->pluck('iteration', 'source_article_version_id')
            ->map(fn ($value) => (int) $value)
            ->all();
    }
}
