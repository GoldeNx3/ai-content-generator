<?php

namespace Modules\Pipeline\Queries;

use Modules\Pipeline\Models\PipelineJob;

final class FindJobByKeyQuery
{
    public function execute(string $key): ?PipelineJob
    {
        return PipelineJob::query()->where('idempotency_key', $key)->first();
    }
}
