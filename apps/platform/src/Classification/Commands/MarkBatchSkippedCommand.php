<?php

namespace Modules\Classification\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Pipeline\Models\PipelineJobBatch;

final class MarkBatchSkippedCommand
{
    public function execute(string $key, int $candidateId): void
    {
        DB::transaction(function () use ($key, $candidateId): void {
            $batch = PipelineJobBatch::query()->whereKey($key)->lockForUpdate()->firstOrFail();
            $batch->update(['skipped_ids' => array_values(array_unique([...$batch->skipped_ids, $candidateId]))]);
        });
    }
}
