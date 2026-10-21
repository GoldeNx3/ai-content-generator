<?php

namespace Modules\WordPress\Commands;

use Modules\WordPress\Models\WordPressConnection;

final class SaveConnectionCommand
{
    public function execute(?WordPressConnection $connection, int $workspaceId, array $attributes): WordPressConnection
    {
        $connection ??= new WordPressConnection(['workspace_id' => $workspaceId]);
        $connection->fill($attributes)->save();

        return $connection;
    }
}
