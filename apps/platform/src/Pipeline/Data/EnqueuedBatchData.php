<?php

namespace Modules\Pipeline\Data;

use Spatie\LaravelData\Data;

final class EnqueuedBatchData extends Data
{
    public function __construct(
        public array $job_ids = [],
        public int $enqueued = 0,
        public int $existing = 0,
        public int $skipped_busy = 0,
        public int $skipped_budget = 0,
    ) {}
}
