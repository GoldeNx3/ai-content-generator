<?php

namespace Modules\Candidates\Queries;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class SimilarTopicsQuery
{
    public function execute(int $workspaceId, int $candidateId, int $windowDays, int $limit): array
    {
        return DB::table('candidates as topic')
            ->join('sources', 'sources.id', '=', 'topic.source_id')
            ->crossJoin(DB::raw('(SELECT embedding, embedding_model FROM candidates WHERE id = '.(int) $candidateId.') AS me'))
            ->where('topic.workspace_id', $workspaceId)
            ->where('topic.id', '!=', $candidateId)
            ->where(fn ($query) => $query->whereNull('topic.topic_group_id')->orWhere('topic.topic_group_id', '!=', $candidateId))
            ->whereNotNull('topic.embedding')
            ->whereNotNull('topic.total_score')
            ->whereColumn('topic.embedding_model', 'me.embedding_model')
            ->whereRaw('cardinality(topic.embedding) = cardinality(me.embedding)')
            ->where('topic.created_at', '>=', CarbonImmutable::now()->subDays($windowDays))
            ->select('topic.id', 'topic.title', 'sources.name as source_name', 'topic.topic_group_id', 'topic.total_score')
            ->selectRaw('(SELECT SUM(a * b) FROM unnest(topic.embedding, me.embedding) AS pair(a, b)) AS similarity')
            ->orderByRaw('similarity DESC NULLS LAST')
            ->limit($limit)
            ->get()
            ->map(fn (object $row) => ['id' => (int) $row->id, 'title' => $row->title, 'source_name' => $row->source_name,
                'topic_group_id' => $row->topic_group_id === null ? null : (int) $row->topic_group_id,
                'total_score' => (int) $row->total_score, 'similarity' => round((float) $row->similarity, 4)])
            ->all();
    }
}
