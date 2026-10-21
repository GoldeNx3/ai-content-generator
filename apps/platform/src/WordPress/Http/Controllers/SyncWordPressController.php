<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\WordPress\Data\SyncData;
use Modules\WordPress\Services\PublicationService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class SyncWordPressController
{
    public function __construct(private readonly PublicationService $publications) {}

    #[Post('article-versions/{version}/wordpress/sync')]
    public function __invoke(Article $version, SyncData $data, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->publications->sync($version, $data, IdempotencyKey::from($request)));
    }
}
