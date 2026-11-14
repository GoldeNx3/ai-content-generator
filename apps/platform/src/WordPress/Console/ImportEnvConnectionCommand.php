<?php

namespace Modules\WordPress\Console;

use Illuminate\Console\Command;
use Modules\Shared\Exceptions\ApiException;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Exceptions\WorkspaceNotResolvedException;
use Modules\Workspaces\Services\ConsoleWorkspaceResolver;

final class ImportEnvConnectionCommand extends Command
{
    protected $signature = 'wordpress:import-env {--workspace= : ID workspace\'u} {--email= : E-mail konta, którego workspace ma dostać połączenie}';

    protected $description = 'Łączy workspace z WordPressem na podstawie WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD';

    public function handle(ConnectionService $connections, ConsoleWorkspaceResolver $workspaces): int
    {
        $env = config('content.wordpress.import');
        if (blank($env['url']) || blank($env['username']) || blank($env['app_password'])) {
            $this->error('Brak WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD w .env');

            return self::FAILURE;
        }
        try {
            $workspaceId = $workspaces->resolve($this->option('workspace'), $this->option('email'));
        } catch (WorkspaceNotResolvedException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }
        if ($connections->find($workspaceId) !== null) {
            $this->error("Workspace {$workspaceId} ma już połączenie WordPress; najpierw je rozłącz w panelu.");

            return self::FAILURE;
        }
        try {
            $connection = $connections->connect($workspaceId, $env['url'], $env['api_url'], $env['username'], $env['app_password'], false);
        } catch (ApiException $exception) {
            $this->error($exception->errorCode);

            return self::FAILURE;
        }
        $this->info("Workspace {$workspaceId} połączony z {$connection->site_url}");

        return self::SUCCESS;
    }
}
