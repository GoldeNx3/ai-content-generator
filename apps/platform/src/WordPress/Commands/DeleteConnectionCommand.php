<?php

namespace Modules\WordPress\Commands;

use Modules\WordPress\Models\WordPressConnection;

final class DeleteConnectionCommand
{
    public function execute(int $workspaceId): void
    {
        WordPressConnection::query()->where('workspace_id', $workspaceId)->delete();
    }
}
