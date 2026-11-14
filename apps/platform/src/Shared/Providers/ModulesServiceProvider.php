<?php

namespace Modules\Shared\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Routing\Router;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;
use Modules\Shared\Routing\WorkspaceBindings;

final class ModulesServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        $this->app->make(WorkspaceBindings::class)->register($this->app->make(Router::class));
        RateLimiter::for('expensive', fn (Request $request) => Limit::perMinute(10)->by('expensive:'.(auth()->id() ?? $request->ip())));
        $this->loadMigrationsFrom(glob(base_path('src/*/Database/Migrations'), GLOB_ONLYDIR) ?: []);

        if ($this->app->runningInConsole()) {
            $this->commands($this->consoleCommands());
        }
    }

    private function consoleCommands(): array
    {
        return array_map(
            fn (string $path): string => 'Modules\\'.str_replace(['/', '.php'], ['\\', ''], substr($path, strlen(base_path('src/')))),
            glob(base_path('src/*/Console/*Command.php')) ?: [],
        );
    }
}
