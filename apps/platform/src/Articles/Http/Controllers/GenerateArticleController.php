<?php

namespace Modules\Articles\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Data\GenerateArticleData;
use Modules\Articles\Services\ArticleService;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class GenerateArticleController
{
    public function __construct(private readonly ArticleService $articles) {}

    #[Post('candidates/{candidate}/article')]
    public function __invoke(Candidate $candidate, GenerateArticleData $data, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->articles->generate($candidate, $data, IdempotencyKey::from($request)));
    }
}
