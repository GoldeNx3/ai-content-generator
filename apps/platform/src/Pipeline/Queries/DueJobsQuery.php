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
            ->get();
    }
}
