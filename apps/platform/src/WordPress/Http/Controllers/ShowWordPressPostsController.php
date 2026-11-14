<?php

namespace Modules\WordPress\Http\Controllers;

use Modules\WordPress\Data\BlogMemoryData;
use Modules\WordPress\Services\BlogMemoryService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowWordPressPostsController
{
    public function __construct(private readonly BlogMemoryService $memory, private readonly CurrentWorkspace $workspace) {}

    #[Get('wordpress/posts')]
    public function __invoke(): BlogMemoryData
    {
        return $this->memory->summary($this->workspace->id());
    }
}
