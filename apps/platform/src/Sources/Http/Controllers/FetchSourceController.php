<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Sources\Models\Source;
use Modules\Sources\Services\IngestionService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class FetchSourceController
{
    public function __construct(private readonly IngestionService $ingestion) {}

    #[Post('sources/{source}/fetch')]
    public function __invoke(Source $source): JsonResponse
    {
        return response()->json($this->ingestion->fetchSource($source));
    }
}
