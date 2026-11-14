<?php

namespace Modules\Demo\Console;

use Illuminate\Console\Command;
use Modules\Demo\Services\DemoSeedService;
use Modules\Workspaces\Exceptions\WorkspaceNotResolvedException;
use Modules\Workspaces\Services\ConsoleWorkspaceResolver;

final class SeedDemoCommand extends Command
{
    protected $signature = 'demo:seed {--workspace= : ID workspace\'u} {--email= : E-mail konta, którego workspace ma dostać tematy}';

    protected $description = 'Tworzy tematy demo przechodzące przez cały pipeline bez kosztów AI';

    public function handle(DemoSeedService $demo, ConsoleWorkspaceResolver $workspaces): int
    {
        try {
            $workspaceId = $workspaces->resolve($this->option('workspace'), $this->option('email'));
        } catch (WorkspaceNotResolvedException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }
        $result = $demo->seed($workspaceId);
        $this->info("DEMO: workspace {$workspaceId}, nowe tematy: {$result['created']}. Akcje na tych tematach nie wywołują płatnego AI.");

        return self::SUCCESS;
    }
}
