<?php

namespace Modules\WordPress\Queries;

use Illuminate\Support\Facades\DB;

final class WordPressPostsQuery
{
    public function execute(int $workspaceId): array
    {
        return DB::table('wordpress_posts')->where('workspace_id', $workspaceId)->orderBy('post_id')
            ->get(['post_id', 'url', 'title', 'excerpt', 'synced_at'])->map(fn ($row) => (array) $row)->all();
    }
}
