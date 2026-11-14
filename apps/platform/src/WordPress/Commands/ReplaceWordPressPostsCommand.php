<?php

namespace Modules\WordPress\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class ReplaceWordPressPostsCommand
{
    public function execute(int $workspaceId, array $posts): void
    {
        DB::transaction(function () use ($workspaceId, $posts): void {
            DB::table('wordpress_posts')->where('workspace_id', $workspaceId)->delete();
            $now = CarbonImmutable::now();
            foreach (array_chunk($posts, 200) as $chunk) {
                DB::table('wordpress_posts')->insert(array_map(fn (array $post) => [
                    'workspace_id' => $workspaceId, 'post_id' => $post['post_id'], 'url' => $post['url'],
                    'title' => $post['title'], 'excerpt' => $post['excerpt'], 'synced_at' => $now,
                ], $chunk));
            }
        });
    }
}
