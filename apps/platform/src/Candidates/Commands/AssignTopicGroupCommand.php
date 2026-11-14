<?php

namespace Modules\Candidates\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class AssignTopicGroupCommand
{
    public function execute(int $candidateId, ?array $vector, ?int $primaryId, ?float $similarity): void
    {
        DB::table('candidates')->where('id', $candidateId)->update([
            'embedding' => $vector === null ? null : Embedding::literal($vector),
            'topic_group_id' => $primaryId,
            'duplicate_similarity' => $similarity,
        ]);
    }
}
