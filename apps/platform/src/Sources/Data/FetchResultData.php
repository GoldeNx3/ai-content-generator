<?php

namespace Modules\Sources\Data;

use Spatie\LaravelData\Data;

final class FetchResultData extends Data
{
    public function __construct(
        public int $sources_processed = 0,
        public int $items_found = 0,
        public int $new_candidates = 0,
        public int $duplicates = 0,
        public int $skipped_old = 0,
        public int $errors = 0,
    ) {}

    public function add(self $other): self
    {
        return new self(
            $this->sources_processed + $other->sources_processed,
            $this->items_found + $other->items_found,
            $this->new_candidates + $other->new_candidates,
            $this->duplicates + $other->duplicates,
            $this->skipped_old + $other->skipped_old,
            $this->errors + $other->errors,
        );
    }
}
