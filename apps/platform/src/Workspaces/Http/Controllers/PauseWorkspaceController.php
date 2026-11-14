<?php

namespace Modules\Workspaces\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Workspaces\Services\CurrentWorkspace;
use Modules\Workspaces\Services\WorkspacePauseService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class PauseWorkspaceController
{
    public function __construct(private readonly WorkspacePauseService $pause, private readonly CurrentWorkspace $workspace) {}

    #[Post('workspace/pause')]
    public function __invoke(): JsonResponse
    {
        $this->workspace->requireOwner();

        return response()->json(['paused_at' => $this->pause->pause($this->workspace->id())->toIso8601ZuluString()]);
    }
}
