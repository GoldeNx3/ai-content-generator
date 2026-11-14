<?php

namespace Modules\Pipeline\Data;

use Modules\Pipeline\Enums\JobKind;
use Spatie\LaravelData\Attributes\Validation\Between;
use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Data;

final class QueueFiltersData extends Data
{
    public function __construct(
        #[In(['active', 'all', 'queued', 'running', 'retrying', 'succeeded', 'failed', 'cancelled'])]
        public string $status = 'active',
        public ?JobKind $kind = null,
        #[Min(1)]
        public ?int $candidate_id = null,
        #[Min(1), Max(10000)]
        public int $page = 1,
        #[Between(1, 100)]
        public int $page_size = 25,
    ) {}
}
