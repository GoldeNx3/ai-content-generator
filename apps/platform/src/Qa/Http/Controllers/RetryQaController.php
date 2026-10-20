<?php

namespace Modules\Qa\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\Qa\Services\QaService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class RetryQaController
{
    public function __construct(private readonly QaService $qa) {}

    #[Post('articles/{article}/qa/retry')]
    public function __invoke(Article $article, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->qa->retry($article, IdempotencyKey::from($request)));
    }
}
