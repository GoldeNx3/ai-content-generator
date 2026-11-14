<?php

namespace Modules\Pipeline\Queries;

use Illuminate\Support\Collection;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class PendingJobsQuery
{
    public function execute(int $workspaceId): Collection
    {
        return PipelineJob::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('status', [JobStatus::Queued->value, JobStatus::Retrying->value])
            ->lockForUpdate()
            ->get();
    }
}
