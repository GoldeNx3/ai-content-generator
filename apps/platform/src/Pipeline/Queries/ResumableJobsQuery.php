<?php

namespace Modules\Pipeline\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class ResumableJobsQuery
{
    public function execute(int $workspaceId): Collection
    {
        return PipelineJob::query()
            ->where('workspace_id', $workspaceId)
            ->whereIn('status', [JobStatus::Queued->value, JobStatus::Retrying->value])
            ->where('available_at', '<=', CarbonImmutable::now())
            ->get();
    }
}
