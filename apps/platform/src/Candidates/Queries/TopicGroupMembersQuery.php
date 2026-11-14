<?php

namespace Modules\Candidates\Queries;

use Illuminate\Support\Facades\DB;

final class TopicGroupMembersQuery
{
    public function execute(int $workspaceId, int $primaryId, int $exceptId): array
    {
        return DB::table('candidates')
            ->join('sources', 'sources.id', '=', 'candidates.source_id')
            ->where('candidates.workspace_id', $workspaceId)
            ->where(fn ($query) => $query->where('candidates.id', $primaryId)->orWhere('candidates.topic_group_id', $primaryId))
            ->where('candidates.id', '!=', $exceptId)
            ->orderByRaw('candidates.id = ? DESC', [$primaryId])
            ->orderBy('candidates.id')
            ->get(['candidates.id', 'candidates.title', 'candidates.external_url', 'sources.name as source_name'])
            ->map(fn ($row) => ['id' => (int) $row->id, 'title' => $row->title, 'external_url' => $row->external_url, 'source_name' => $row->source_name])
            ->all();
    }
}
