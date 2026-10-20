<?php

namespace Modules\Articles\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Articles\Services\ArticleViewService;
use Modules\Candidates\Models\Candidate;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ListArticleVersionsController
{
    public function __construct(private readonly ArticleViewService $views) {}

    #[Get('candidates/{candidate}/articles')]
    public function __invoke(Candidate $candidate): JsonResponse
    {
        return response()->json($this->views->summaries($candidate->id));
    }
}
