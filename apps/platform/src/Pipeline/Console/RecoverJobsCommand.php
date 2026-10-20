<?php

namespace Modules\Pipeline\Console;

use Illuminate\Console\Command;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Queries\DueJobsQuery;
use Modules\Pipeline\Queries\StaleRunningJobsQuery;
use Modules\Pipeline\Services\JobRunner;

final class RecoverJobsCommand extends Command
{
    protected $signature = 'pipeline:recover {--redispatch-after=300 : Sekundy, po których zaległy job wraca do kolejki}';

    protected $description = 'Odzyskuje joby przerwanych workerów i zgubione w kolejce';

    public function handle(StaleRunningJobsQuery $stale, DueJobsQuery $due, JobRunner $runner): int
    {
        foreach ($stale->execute() as $job) {
            $runner->recoverLost($job);
        }
        foreach ($due->execute((int) $this->option('redispatch-after')) as $job) {
            RunPipelineJob::dispatch($job->id, $job->kind->value);
        }

        return self::SUCCESS;
    }
}
