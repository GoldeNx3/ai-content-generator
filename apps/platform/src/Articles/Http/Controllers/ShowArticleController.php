<?php

namespace Modules\Articles\Http\Controllers;

use Modules\Articles\Data\ArticleData;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ArticleViewService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowArticleController
{
    public function __construct(private readonly ArticleViewService $views) {}

    #[Get('articles/{article}')]
    public function __invoke(Article $article): ArticleData
    {
        return $this->views->details($article);
    }
}
