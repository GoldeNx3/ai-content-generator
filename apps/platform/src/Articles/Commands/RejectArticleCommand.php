<?php

namespace Modules\Articles\Commands;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;

final class RejectArticleCommand
{
    public function execute(Article $article, ?string $reason): void
    {
        $article->update(['status' => ArticleStatus::Rejected, 'rejection_reason' => $reason]);
    }
}
