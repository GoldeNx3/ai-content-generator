<?php

namespace Modules\Workspaces\Providers;

use Illuminate\Support\ServiceProvider;
use Modules\Workspaces\Services\CurrentWorkspace;

final class WorkspacesServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->scoped(CurrentWorkspace::class);
    }
}
