<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Sources\Services\IngestionService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware(['auth:sanctum', 'throttle:expensive'])]
final class FetchAllSourcesController
{
    public function __construct(private readonly IngestionService $ingestion, private readonly CurrentWorkspace $workspace) {}

    #[Post('sources/fetch')]
    public function __invoke(): JsonResponse
    {
        return response()->json($this->ingestion->fetchAllActive($this->workspace->id()));
    }
}
