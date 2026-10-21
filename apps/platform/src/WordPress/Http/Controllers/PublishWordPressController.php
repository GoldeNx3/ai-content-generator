<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\WordPress\Data\PublishData;
use Modules\WordPress\Services\PublicationService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class PublishWordPressController
{
    public function __construct(private readonly PublicationService $publications) {}

    #[Post('article-versions/{version}/wordpress')]
    public function __invoke(Article $version, PublishData $data, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->publications->publish($version, $data, IdempotencyKey::from($request)));
    }
}
