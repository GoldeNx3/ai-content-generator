<?php

namespace Modules\Pipeline\Console;

use Illuminate\Console\Command;
use Illuminate\Contracts\Queue\ClearableQueue;
use Illuminate\Support\Facades\Queue;
use Modules\Pipeline\Commands\WipeDomainDataCommand;

final class WipeDataCommand extends Command
{
    protected $signature = 'data:wipe {--force : Bez pytania o potwierdzenie}';

    protected $description = 'Usuwa dane domenowe i zadania kolejki pipeline (konta, workspace\'y i połączenia WordPress zostają)';

    public function handle(WipeDomainDataCommand $wipe): int
    {
        if (! $this->option('force') && ! $this->confirm('Usunąć źródła, kandydatów, artykuły i zadania?')) {
            return self::FAILURE;
        }
        $wipe->execute();
        $queue = Queue::connection();
        $cleared = $queue instanceof ClearableQueue ? $queue->clear('pipeline') : 0;
        $this->info("Dane wyczyszczone, usunięto {$cleared} zadań z kolejki.");

        return self::SUCCESS;
    }
}
