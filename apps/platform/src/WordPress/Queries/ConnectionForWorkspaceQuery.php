<?php

namespace Modules\WordPress\Queries;

use Modules\WordPress\Models\WordPressConnection;

final class ConnectionForWorkspaceQuery
{
    public function execute(int $workspaceId): ?WordPressConnection
    {
        return WordPressConnection::query()->where('workspace_id', $workspaceId)->first();
    }
}
