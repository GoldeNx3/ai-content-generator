<?php

namespace Modules\Articles\Commands;

use Carbon\CarbonImmutable;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;

final class ApproveArticleCommand
{
    public function execute(Article $article): void
    {
        Article::query()->where('candidate_id', $article->candidate_id)->where('status', ArticleStatus::Approved->value)
            ->whereKeyNot($article->id)->update(['status' => ArticleStatus::Superseded->value]);
        $article->update(['status' => ArticleStatus::Approved, 'approved_at' => CarbonImmutable::now(), 'approved_by' => null]);
    }
}
