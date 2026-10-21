<?php

namespace Modules\WordPress\Queries;

use Modules\WordPress\Models\WordPressPublication;

final class LinkedPublicationsQuery
{
    public function exists(int $workspaceId, string $instanceId): bool
    {
        return WordPressPublication::query()
            ->join('candidates', 'candidates.id', '=', 'wordpress_publications.candidate_id')
            ->where('candidates.workspace_id', $workspaceId)
            ->where('wordpress_publications.wordpress_instance_id', $instanceId)
            ->whereNotNull('wordpress_publications.wordpress_post_id')
            ->exists();
    }
}
