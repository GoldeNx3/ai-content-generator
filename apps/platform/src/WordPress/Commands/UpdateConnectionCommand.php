<?php

namespace Modules\WordPress\Commands;

use Modules\WordPress\Models\WordPressConnection;

final class UpdateConnectionCommand
{
    public function execute(WordPressConnection $connection, array $attributes): WordPressConnection
    {
        $connection->update($attributes);

        return $connection;
    }
}
