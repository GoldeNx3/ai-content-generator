<?php

namespace Modules\Articles\Http\Controllers;

use Modules\Articles\Data\ArticleData;
use Modules\Articles\Data\ArticleUpdateData;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ArticleService;
use Modules\Articles\Services\ArticleViewService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateArticleController
{
    public function __construct(private readonly ArticleService $articles, private readonly ArticleViewService $views) {}

    #[Patch('articles/{article}')]
    public function __invoke(Article $article, ArticleUpdateData $data): ArticleData
    {
        return $this->views->details($this->articles->update($article, $data));
    }
}
