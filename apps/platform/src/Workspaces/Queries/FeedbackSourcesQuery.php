<?php

namespace Modules\Workspaces\Queries;

use Modules\Articles\Models\Article;

final class FeedbackSourcesQuery
{
    public function execute(int $candidateId): array
    {
        $edited = Article::query()->where('candidate_id', $candidateId)->where('is_edited', true)
            ->whereNotNull('generated_content')->whereColumn('generated_content', '!=', 'content')
            ->orderByDesc('version')->first();
        $rejections = Article::query()->where('candidate_id', $candidateId)->whereNotNull('rejection_reason')
            ->where('rejection_reason', '!=', '')->orderByDesc('version')->limit(10)->pluck('rejection_reason')->all();

        return [$edited, $rejections];
    }
}
