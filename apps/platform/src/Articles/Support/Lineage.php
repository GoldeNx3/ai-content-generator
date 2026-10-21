<?php

namespace Modules\Articles\Support;

final class Lineage
{
    public static function walk(array $versions, int $articleId): array
    {
        $lineage = [];
        $current = $versions[$articleId] ?? null;
        while ($current !== null && ! in_array($current->id, $lineage, true)) {
            $lineage[] = $current->id;
            if (in_array($current->created_by, ['generated', 'regenerated', 'legacy'], true)) {
                break;
            }
            $current = $current->parent_version_id ? ($versions[$current->parent_version_id] ?? null) : null;
        }

        return $lineage;
    }
}
