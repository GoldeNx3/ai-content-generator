<?php

namespace Modules\Sources\Queries;

use Illuminate\Support\Collection;
use Modules\Sources\Models\Source;

final class ListSourcesQuery
{
    public function execute(int $workspaceId, bool $activeOnly = false): Collection
    {
        return Source::query()
            ->where('workspace_id', $workspaceId)
            ->when($activeOnly, fn ($query) => $query->where('active', true))
            ->orderBy('name')
            ->orderBy('id')
            ->get();
    }
}
