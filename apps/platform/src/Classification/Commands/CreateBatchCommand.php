<?php

namespace Modules\Classification\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Models\PipelineJobBatch;

final class CreateBatchCommand
{
    public function execute(string $key, int $workspaceId, string $hash, array $candidateIds): PipelineJobBatch
    {
        DB::table('pipeline_job_batches')->insertOrIgnore([
            'id' => $key, 'workspace_id' => $workspaceId, 'request_hash' => $hash,
            'candidate_ids' => json_encode($candidateIds), 'skipped_ids' => '[]', 'created_at' => now(),
        ]);

        return PipelineJobBatch::query()->findOrFail($key);
    }
}
