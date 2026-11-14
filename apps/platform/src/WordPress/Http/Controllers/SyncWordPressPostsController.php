<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\WordPress\Services\BlogMemoryService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware(['auth:sanctum', 'throttle:expensive'])]
final class SyncWordPressPostsController
{
    public function __construct(private readonly BlogMemoryService $memory, private readonly CurrentWorkspace $workspace) {}

    #[Post('wordpress/posts/sync')]
    public function __invoke(): JsonResponse
    {
        return response()->json($this->memory->sync($this->workspace->id()));
    }
}
