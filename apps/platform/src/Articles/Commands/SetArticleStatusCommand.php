<?php

namespace Modules\Articles\Commands;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;

final class SetArticleStatusCommand
{
    public function execute(Article $article, ArticleStatus $status): void
    {
        $article->update(['status' => $status]);
    }
}
