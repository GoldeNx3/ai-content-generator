<?php

namespace Modules\Sources\Queries;

use Modules\Sources\Models\Source;

final class SourceCountQuery
{
    public function execute(int $workspaceId): int
    {
        return Source::query()->where('workspace_id', $workspaceId)->count();
    }
}
