<?php

namespace Modules\Candidates\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class LeaveTopicGroupCommand
{
    public function execute(int $candidateId, string $reason): void
    {
        DB::table('candidates')->where('id', $candidateId)->update([
            'topic_group_id' => null,
            'duplicate_similarity' => null,
            'llm_reason' => $reason,
            'updated_at' => CarbonImmutable::now(),
        ]);
    }
}
