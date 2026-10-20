<?php

namespace Modules\Sources\Queries;

use Modules\Sources\Models\Source;

final class FindWorkspaceSourceQuery
{
    public function execute(int $id, int $workspaceId): ?Source
    {
        return Source::query()->whereKey($id)->where('workspace_id', $workspaceId)->first();
    }
}
