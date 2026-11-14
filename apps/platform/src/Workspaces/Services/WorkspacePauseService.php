<?php

namespace Modules\Workspaces\Services;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Queries\ResumableJobsQuery;
use Modules\Workspaces\Commands\SetWorkspacePausedCommand;

final class WorkspacePauseService
{
    public function __construct(
        private readonly SetWorkspacePausedCommand $setPaused,
        private readonly ResumableJobsQuery $resumable,
    ) {}

    public function pause(int $workspaceId): CarbonImmutable
    {
        $now = CarbonImmutable::now();
        $this->setPaused->execute($workspaceId, $now);

        return $now;
    }

    public function resume(int $workspaceId): int
    {
        $this->setPaused->execute($workspaceId, null);
        $jobs = $this->resumable->execute($workspaceId);
        foreach ($jobs as $job) {
            RunPipelineJob::dispatch($job->id, $job->kind->value);
        }

        return $jobs->count();
    }
}
