<?php

namespace Modules\Candidates\Data;

use Modules\Candidates\Enums\CandidateStatus;
use Spatie\LaravelData\Attributes\Validation\Required;
use Spatie\LaravelData\Data;

final class StatusUpdateData extends Data
{
    public function __construct(
        #[Required]
        public CandidateStatus $status,
    ) {}
}
