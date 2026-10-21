<?php

namespace Modules\Candidates\Support;

final class WorkflowStatusExpression
{
    public static function sql(): string
    {
        return <<<'SQL'
COALESCE(
    (SELECT CASE wp.wp_status WHEN 'publish' THEN 'published' WHEN 'draft' THEN 'draft' WHEN 'future' THEN 'scheduled' END
       FROM wordpress_publications wp
      WHERE wp.candidate_id = candidates.id AND wp.wordpress_post_id IS NOT NULL AND wp.last_synced_at IS NOT NULL),
    CASE WHEN candidates.status = 'ignored' THEN 'ignored'
         ELSE COALESCE(
            (SELECT CASE WHEN a.status = 'approved' THEN 'approved' ELSE 'draft' END
               FROM articles a WHERE a.candidate_id = candidates.id AND a.is_current),
            candidates.status)
    END
)
SQL;
    }
}
