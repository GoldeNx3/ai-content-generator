<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Sources\Services\SourceService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ListSourcesController
{
    public function __construct(private readonly SourceService $sources, private readonly CurrentWorkspace $workspace) {}

    #[Get('sources')]
    public function __invoke(): JsonResponse
    {
        return response()->json($this->sources->list($this->workspace->id()));
    }
}
