<?php

namespace Modules\Demo\Queries;

use Modules\Sources\Models\Source;

final class DemoSourceQuery
{
    public function execute(int $workspaceId, string $url): ?Source
    {
        return Source::query()->where('workspace_id', $workspaceId)->where('url', $url)->first();
    }
}
