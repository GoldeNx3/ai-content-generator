<?php

namespace Modules\Workspaces\Console;

use Illuminate\Console\Command;
use Modules\Workspaces\Commands\SetWorkspaceBudgetCommand;

final class SetBudgetCommand extends Command
{
    protected $signature = 'workspaces:budget {workspace} {usd : Kwota w USD albo "default"}';

    protected $description = 'Ustawia miesięczny budżet AI workspace\'u';

    public function handle(SetWorkspaceBudgetCommand $setBudget): int
    {
        $usd = (string) $this->argument('usd');
        if ($usd !== 'default' && (! is_numeric($usd) || (float) $usd < 0 || (float) $usd >= 100_000_000)) {
            $this->error('Podaj kwotę >= 0 albo "default"');

            return self::FAILURE;
        }
        $workspace = $setBudget->execute((int) $this->argument('workspace'), $usd === 'default' ? null : number_format((float) $usd, 2, '.', ''));
        $this->info("Workspace {$workspace->id}: ".($workspace->monthly_budget_usd ?? 'domyślny').' USD / miesiąc');

        return self::SUCCESS;
    }
}
