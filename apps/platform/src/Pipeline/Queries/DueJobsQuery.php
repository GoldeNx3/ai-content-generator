<?php

namespace Modules\Pipeline\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class DueJobsQuery
{
    public function execute(int $olderThanSeconds): Collection
    {
        return PipelineJob::query()
            ->whereIn('status', [JobStatus::Queued->value, JobStatus::Retrying->value])
            ->where('available_at', '<', CarbonImmutable::now()->subSeconds($olderThanSeconds))
            ->whereNotExists(fn ($query) => $query->from('workspaces')
                ->whereColumn('workspaces.id', 'pipeline_jobs.workspace_id')
                ->whereNotNull('workspaces.paused_at'))
            ->get();
    }
}
