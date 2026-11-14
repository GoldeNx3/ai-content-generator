<?php

namespace Modules\WordPress\Queries;

use Illuminate\Support\Facades\DB;

final class SimilarBlogPostQuery
{
    public function execute(int $workspaceId, string $title, float $minimum): ?object
    {
        return DB::table('wordpress_posts')
            ->where('workspace_id', $workspaceId)
            ->select('title', 'url')
            ->selectRaw('similarity(title, ?) AS similarity', [$title])
            ->whereRaw('similarity(title, ?) >= ?', [$title, $minimum])
            ->orderByDesc('similarity')
            ->first();
    }
}
