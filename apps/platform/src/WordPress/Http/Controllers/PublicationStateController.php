<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Articles\Models\Article;
use Modules\WordPress\Services\PublicationService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class PublicationStateController
{
    public function __construct(private readonly PublicationService $publications) {}

    #[Get('article-versions/{version}/wordpress')]
    public function __invoke(Article $version): JsonResponse
    {
        return response()->json($this->publications->state($version));
    }
}
