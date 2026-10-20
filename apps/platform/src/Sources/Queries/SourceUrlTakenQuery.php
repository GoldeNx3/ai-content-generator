<?php

namespace Modules\Sources\Queries;

use Modules\Sources\Models\Source;

final class SourceUrlTakenQuery
{
    public function execute(string $url, int $workspaceId, ?int $exceptId = null): bool
    {
        return Source::query()
            ->where('workspace_id', $workspaceId)
            ->where('url', $url)
            ->when($exceptId !== null, fn ($query) => $query->whereKeyNot($exceptId))
            ->exists();
    }
}
