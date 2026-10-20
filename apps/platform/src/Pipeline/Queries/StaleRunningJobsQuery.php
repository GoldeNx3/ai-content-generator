<?php

namespace Modules\Pipeline\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class StaleRunningJobsQuery
{
    public function execute(): Collection
    {
        return PipelineJob::query()
            ->where('status', JobStatus::Running->value)
            ->where('lease_expires_at', '<', CarbonImmutable::now())
            ->get();
    }
}
