<?php

namespace Modules\AutoFix\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Articles\Models\Article;
use Modules\AutoFix\Services\AutoFixService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class FixHistoryController
{
    public function __construct(private readonly AutoFixService $autoFix) {}

    #[Get('article-versions/{version}/fixes')]
    public function __invoke(Article $version): JsonResponse
    {
        return response()->json($this->autoFix->history($version));
    }
}
