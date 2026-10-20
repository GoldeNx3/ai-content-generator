<?php

namespace Modules\Classification\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Models\PipelineJobBatch;

final class BatchCommand
{
    public function create(string $key, int $workspaceId, string $hash, array $candidateIds): PipelineJobBatch
    {
        DB::table('pipeline_job_batches')->insertOrIgnore([
            'id' => $key, 'workspace_id' => $workspaceId, 'request_hash' => $hash,
            'candidate_ids' => json_encode($candidateIds), 'skipped_ids' => '[]', 'created_at' => now(),
        ]);

        return PipelineJobBatch::query()->findOrFail($key);
    }

    public function find(string $key): ?PipelineJobBatch
    {
        return PipelineJobBatch::query()->find($key);
    }

    public function markSkipped(string $key, int $candidateId): void
    {
        DB::transaction(function () use ($key, $candidateId): void {
            $batch = PipelineJobBatch::query()->whereKey($key)->lockForUpdate()->firstOrFail();
            $batch->update(['skipped_ids' => array_values(array_unique([...$batch->skipped_ids, $candidateId]))]);
        });
    }
}
