<?php

namespace Modules\Classification\Console;

use Illuminate\Console\Command;
use Modules\Classification\Services\ScheduledPipelineService;

final class RunScheduledPipelineCommand extends Command
{
    protected $signature = 'pipeline:scheduled';

    protected $description = 'Pobiera RSS wszystkich workspace\'ów i zleca ocenę nowych tematów (z budżetem per workspace)';

    public function handle(ScheduledPipelineService $pipeline): int
    {
        $result = $pipeline->run();
        $this->info(sprintf('Nowe tematy: %d, zlecone oceny: %d', $result['fetch']->new_candidates, $result['enqueued']));

        return self::SUCCESS;
    }
}
