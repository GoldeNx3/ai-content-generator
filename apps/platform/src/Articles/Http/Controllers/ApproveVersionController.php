<?php

namespace Modules\Articles\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ApprovalService;
use Modules\Articles\Services\ArticleViewService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ApproveVersionController
{
    public function __construct(private readonly ApprovalService $approval, private readonly ArticleViewService $views) {}

    #[Post('article-versions/{version}/approve')]
    public function __invoke(Article $version): JsonResponse
    {
        return response()->json($this->views->details($this->approval->approve($version)));
    }
}
