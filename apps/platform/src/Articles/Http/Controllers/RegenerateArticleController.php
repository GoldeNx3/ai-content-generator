<?php

namespace Modules\Articles\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Data\GenerateArticleData;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ArticleService;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class RegenerateArticleController
{
    public function __construct(private readonly ArticleService $articles) {}

    #[Post('articles/{article}/regenerate')]
    public function __invoke(Article $article, GenerateArticleData $data, Request $request): JsonResponse
    {
        $overrides = array_intersect_key($data->options(), $request->all());

        return JobResponse::accepted($this->articles->regenerate($article, $overrides, IdempotencyKey::from($request)));
    }
}
