<?php

namespace Modules\Candidates\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class AssignTopicGroupCommand
{
    public function execute(int $candidateId, ?array $vector, ?string $model, ?int $primaryId, ?float $similarity): void
    {
        DB::table('candidates')->where('id', $candidateId)->update([
            'embedding' => $vector === null ? null : Embedding::literal($vector),
            'embedding_model' => $vector === null ? null : $model,
            'topic_group_id' => $primaryId,
            'duplicate_similarity' => $similarity,
        ]);
    }
}
