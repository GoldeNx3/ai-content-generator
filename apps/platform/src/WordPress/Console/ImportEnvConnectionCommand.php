<?php

namespace Modules\WordPress\Console;

use Illuminate\Console\Command;
use Modules\Shared\Exceptions\ApiException;
use Modules\WordPress\Services\ConnectionService;
use Modules\Workspaces\Queries\OldestWorkspaceQuery;

final class ImportEnvConnectionCommand extends Command
{
    protected $signature = 'wordpress:import-env {--workspace= : ID workspace\'u (domyślnie najstarszy)}';

    protected $description = 'Łączy workspace z WordPressem na podstawie WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD';

    public function handle(ConnectionService $connections, OldestWorkspaceQuery $oldest): int
    {
        $env = config('content.wordpress.import');
        if (blank($env['url']) || blank($env['username']) || blank($env['app_password'])) {
            $this->error('Brak WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD w .env');

            return self::FAILURE;
        }
        $workspaceId = $this->option('workspace') ? (int) $this->option('workspace') : $oldest->execute()?->id;
        if ($workspaceId === null) {
            $this->error('Brak workspace\'u: najpierw załóż konto.');

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
