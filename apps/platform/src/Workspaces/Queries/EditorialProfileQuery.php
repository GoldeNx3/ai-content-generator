<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\Workspace;

final class EditorialProfileQuery
{
    public function execute(int $workspaceId): ?array
    {
        return Workspace::query()->whereKey($workspaceId)->value('editorial_profile');
    }
}
