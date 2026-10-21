<?php

namespace Modules\Classification\Queries;

use Modules\Pipeline\Models\PipelineJobBatch;

final class FindBatchQuery
{
    public function execute(string $key): ?PipelineJobBatch
    {
        return PipelineJobBatch::query()->find($key);
    }
}
