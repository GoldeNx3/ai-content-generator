<?php

namespace Modules\Candidates\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class NearestTopicQuery
{
    public function execute(int $workspaceId, int $candidateId, array $vector, ?string $model, int $windowDays, int $maxCompared): ?object
    {
        $recent = DB::table('candidates')
            ->where('workspace_id', $workspaceId)
            ->where('id', '!=', $candidateId)
            ->where(fn ($query) => $query->whereNull('topic_group_id')->orWhere('topic_group_id', '!=', $candidateId))
            ->whereNotNull('embedding')
            ->whereNotNull('total_score')
            ->where('embedding_model', $model)
            ->whereRaw('cardinality(embedding) = ?', [count($vector)])
            ->where('created_at', '>=', CarbonImmutable::now()->subDays($windowDays))
            ->orderByDesc('created_at')
            ->limit($maxCompared)
            ->select('id', 'title', 'topic_group_id', 'embedding');

        return DB::query()->fromSub($recent, 'recent')
            ->select('id', 'title', 'topic_group_id')
            ->selectRaw('(SELECT SUM(a * b) FROM unnest(embedding, ?::real[]) AS pair(a, b)) AS similarity', [Embedding::literal($vector)])
            ->orderByRaw('similarity DESC NULLS LAST')
            ->first();
    }
}
