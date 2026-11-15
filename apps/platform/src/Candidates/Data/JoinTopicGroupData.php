<?php

namespace Modules\Candidates\Data;

use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Data;

final class JoinTopicGroupData extends Data
{
    public function __construct(
        #[Min(1)]
        public int $primary_id,
    ) {}
}
