<?php

namespace Modules\Demo\Http\Controllers;

use Modules\Demo\Data\DemoResetData;
use Modules\Demo\Services\DemoSeedService;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ResetDemoController
{
    public function __construct(private readonly DemoSeedService $demo, private readonly CurrentWorkspace $workspace) {}

    #[Post('demo/reset')]
    public function __invoke(): DemoResetData
    {
        return $this->demo->reset($this->workspace->id());
    }
}
