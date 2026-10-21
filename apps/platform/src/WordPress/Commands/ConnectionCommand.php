<?php

namespace Modules\WordPress\Commands;

use Illuminate\Support\Facades\DB;
use Modules\WordPress\Models\WordPressConnection;
use Modules\WordPress\Models\WordPressPublication;

final class ConnectionCommand
{
    public function save(?WordPressConnection $connection, int $workspaceId, array $attributes): WordPressConnection
    {
        $connection ??= new WordPressConnection(['workspace_id' => $workspaceId]);
        $connection->fill($attributes)->save();

        return $connection;
    }

    public function delete(int $workspaceId): void
    {
        WordPressConnection::query()->where('workspace_id', $workspaceId)->delete();
    }

    public function unlinkPublications(int $workspaceId, string $instanceId): void
    {
        WordPressPublication::query()
            ->whereIn('candidate_id', DB::table('candidates')->where('workspace_id', $workspaceId)->select('id'))
            ->where('wordpress_instance_id', $instanceId)
            ->update([
                'wordpress_post_id' => null, 'wordpress_instance_id' => null, 'wordpress_url' => null, 'wp_status' => null,
                'status' => 'not_sent', 'last_synced_at' => null, 'last_synced_content_hash' => null, 'media_id' => null,
                'media_fingerprint' => null, 'conflict' => null, 'error_code' => null,
            ]);
    }
}
