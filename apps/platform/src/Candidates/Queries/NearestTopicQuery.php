<?php

namespace Modules\Candidates\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class NearestTopicQuery
{
    public function execute(int $workspaceId, int $candidateId, array $vector, int $windowDays): ?object
    {
        return DB::table('candidates')
            ->where('workspace_id', $workspaceId)
            ->where('id', '!=', $candidateId)
            ->whereNotNull('embedding')
            ->whereNotNull('total_score')
            ->where('created_at', '>=', CarbonImmutable::now()->subDays($windowDays))
            ->select('id', 'title', 'topic_group_id')
            ->selectRaw('(SELECT SUM(a * b) FROM unnest(embedding, ?::real[]) AS pair(a, b)) AS similarity', [Embedding::literal($vector)])
            ->orderByRaw('similarity DESC NULLS LAST')
            ->first();
    }
}
