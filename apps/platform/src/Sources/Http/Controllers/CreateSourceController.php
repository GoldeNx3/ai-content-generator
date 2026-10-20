<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Sources\Data\CreateSourceData;
use Modules\Sources\Services\SourceService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class CreateSourceController
{
    public function __construct(private readonly SourceService $sources, private readonly CurrentWorkspace $workspace) {}

    #[Post('sources')]
    public function __invoke(CreateSourceData $data): JsonResponse
    {
        return response()->json($this->sources->create($this->workspace->id(), $data), 201);
    }
}
