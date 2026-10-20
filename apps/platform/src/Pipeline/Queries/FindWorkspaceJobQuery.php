<?php

namespace Modules\Pipeline\Queries;

use Illuminate\Support\Str;
use Modules\Pipeline\Models\PipelineJob;

final class FindWorkspaceJobQuery
{
    public function execute(string $id, int $workspaceId): ?PipelineJob
    {
        if (! Str::isUuid($id)) {
            return null;
        }

        return PipelineJob::query()->whereKey($id)->where('workspace_id', $workspaceId)->first();
    }
}
