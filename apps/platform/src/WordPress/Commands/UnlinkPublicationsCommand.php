<?php

namespace Modules\WordPress\Commands;

use Illuminate\Support\Facades\DB;
use Modules\WordPress\Models\WordPressPublication;

final class UnlinkPublicationsCommand
{
    public function execute(int $workspaceId, string $instanceId): void
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
