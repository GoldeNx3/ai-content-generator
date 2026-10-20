<?php

namespace Modules\Shared\Providers;

use Illuminate\Support\ServiceProvider;

final class ModulesServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
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
