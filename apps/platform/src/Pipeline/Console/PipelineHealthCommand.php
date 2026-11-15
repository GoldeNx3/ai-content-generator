<?php

namespace Modules\Pipeline\Console;

use Illuminate\Console\Command;
use Modules\Pipeline\Services\PipelineHealthService;

final class PipelineHealthCommand extends Command
{
    protected $signature = 'pipeline:health';

    protected $description = 'Sprawdza kolejkę i wysyła alert na ALERT_WEBHOOK_URL (Slack/Discord) przy problemie';

    public function handle(PipelineHealthService $health): int
    {
        $health->check();

        return self::SUCCESS;
    }
}
