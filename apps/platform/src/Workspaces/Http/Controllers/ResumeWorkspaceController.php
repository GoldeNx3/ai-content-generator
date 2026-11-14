<?php

namespace Modules\Workspaces\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Workspaces\Services\CurrentWorkspace;
use Modules\Workspaces\Services\WorkspacePauseService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ResumeWorkspaceController
{
    public function __construct(private readonly WorkspacePauseService $pause, private readonly CurrentWorkspace $workspace) {}

    #[Post('workspace/resume')]
    public function __invoke(): JsonResponse
    {
        $this->workspace->requireOwner();

        return response()->json(['paused_at' => null, 'resumed_jobs' => $this->pause->resume($this->workspace->id())]);
    }
}
