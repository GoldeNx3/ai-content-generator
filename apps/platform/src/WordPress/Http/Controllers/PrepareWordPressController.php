<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\WordPress\Services\PublicationService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class PrepareWordPressController
{
    public function __construct(private readonly PublicationService $publications) {}

    #[Post('article-versions/{version}/wordpress/prepare')]
    public function __invoke(Article $version, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->publications->prepare($version, IdempotencyKey::from($request)));
    }
}
