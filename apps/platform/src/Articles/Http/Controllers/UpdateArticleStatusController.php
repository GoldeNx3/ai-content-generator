<?php

namespace Modules\Articles\Http\Controllers;

use Modules\Articles\Data\ArticleData;
use Modules\Articles\Data\ArticleStatusData;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ArticleService;
use Modules\Articles\Services\ArticleViewService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateArticleStatusController
{
    public function __construct(private readonly ArticleService $articles, private readonly ArticleViewService $views) {}

    #[Patch('articles/{article}/status')]
    public function __invoke(Article $article, ArticleStatusData $data): ArticleData
    {
        return $this->views->details($this->articles->setStatus($article, $data->status));
    }
}
