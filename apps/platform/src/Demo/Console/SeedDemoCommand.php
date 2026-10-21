<?php

namespace Modules\Demo\Console;

use Illuminate\Console\Command;
use Modules\Demo\Services\DemoSeedService;
use Modules\Workspaces\Queries\OldestWorkspaceQuery;

final class SeedDemoCommand extends Command
{
    protected $signature = 'demo:seed {--workspace= : ID workspace\'u (domyślnie najstarszy)}';

    protected $description = 'Tworzy tematy demo przechodzące przez cały pipeline bez kosztów AI';

    public function handle(DemoSeedService $demo, OldestWorkspaceQuery $oldest): int
    {
        $workspaceId = $this->option('workspace') ? (int) $this->option('workspace') : $oldest->execute()?->id;
        if ($workspaceId === null) {
            $this->error('Brak workspace\'u: najpierw załóż konto (php artisan users:create EMAIL).');

            return self::FAILURE;
        }
        $result = $demo->seed($workspaceId);
        $this->info("DEMO: workspace {$workspaceId}, nowe tematy: {$result['created']}. Akcje na tych tematach nie wywołują płatnego AI.");

        return self::SUCCESS;
    }
}
