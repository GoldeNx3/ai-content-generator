<?php

namespace Modules\Articles\Commands;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;

final class UpdateArticleQaStateCommand
{
    public function execute(Article $article, bool $qaPassed, ArticleStatus $status): void
    {
        $article->update(['qa_passed' => $qaPassed, 'status' => $status]);
    }
}
