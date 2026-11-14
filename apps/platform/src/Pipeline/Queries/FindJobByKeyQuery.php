<?php

namespace Modules\Pipeline\Queries;

use Modules\Pipeline\Models\PipelineJob;

final class FindJobByKeyQuery
{
    public function execute(int $workspaceId, string $key): ?PipelineJob
    {
        return PipelineJob::query()->where('workspace_id', $workspaceId)->where('idempotency_key', $key)->first();
    }
}
