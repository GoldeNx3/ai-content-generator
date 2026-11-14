<?php

namespace Modules\Classification\Console;

use Illuminate\Console\Command;
use Modules\Classification\Services\ScheduledPipelineService;
use Modules\Shared\Exceptions\ApiException;
use Modules\Workspaces\Exceptions\WorkspaceNotResolvedException;
use Modules\Workspaces\Services\ConsoleWorkspaceResolver;

final class RunScheduledPipelineCommand extends Command
{
    protected $signature = 'pipeline:scheduled
        {--workspace= : ID workspace\'u – jednorazowy przebieg tylko dla niego}
        {--email= : E-mail konta – jednorazowy przebieg tylko dla jego workspace\'u}';

    protected $description = 'Bez opcji: automatyka workspace\'ów, którym minął interwał. Z --email/--workspace: pobranie RSS i ocena dla jednego workspace\'u';

    public function handle(ScheduledPipelineService $pipeline, ConsoleWorkspaceResolver $workspaces): int
    {
        if (blank($this->option('workspace')) && blank($this->option('email'))) {
            if (! config('content.automation.enabled')) {
                $this->info('Automatyka wyłączona (AUTOMATION_ENABLED=false).');

                return self::SUCCESS;
            }
            $result = $pipeline->runDue();
            $this->info(sprintf('Workspace\'y: %d, nowe tematy: %d, zlecone oceny: %d', $result['workspaces'], $result['new_candidates'], $result['enqueued']));

            return self::SUCCESS;
        }
        try {
            $workspaceId = $workspaces->resolve($this->option('workspace'), $this->option('email'));
            $result = $pipeline->runWorkspace($workspaceId, automatic: false);
        } catch (WorkspaceNotResolvedException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        } catch (ApiException $exception) {
            $this->error($exception->errorCode === 'workspace_paused'
                ? 'Workspace jest wstrzymany. Wznów go w Ustawieniach panelu.'
                : $exception->errorCode);

            return self::FAILURE;
        }
        $this->info(sprintf('Workspace %d: nowe tematy: %d, zlecone oceny: %d%s', $workspaceId, $result['new_candidates'], $result['enqueued'],
            $result['budget_exceeded'] ? ' (budżet wyczerpany)' : ''));

        return self::SUCCESS;
    }
}
