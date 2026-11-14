<?php

namespace Modules\WordPress\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class ReplaceWordPressPostsCommand
{
    public function execute(int $workspaceId, array $posts, bool $synced): void
    {
        DB::transaction(function () use ($workspaceId, $posts, $synced): void {
            DB::table('wordpress_posts')->where('workspace_id', $workspaceId)->delete();
            $now = CarbonImmutable::now();
            DB::table('wordpress_connections')->where('workspace_id', $workspaceId)->update(['posts_synced_at' => $synced ? $now : null]);
            foreach (array_chunk($posts, 200) as $chunk) {
                DB::table('wordpress_posts')->insert(array_map(fn (array $post) => [
                    'workspace_id' => $workspaceId, 'post_id' => $post['post_id'], 'url' => $post['url'],
                    'title' => $post['title'], 'excerpt' => $post['excerpt'], 'synced_at' => $now,
                ], $chunk));
            }
        });
    }
}
