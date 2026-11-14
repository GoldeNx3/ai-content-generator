<?php

namespace Modules\Candidates\Data;

use Modules\Candidates\Enums\CandidateCategory;
use Modules\Candidates\Enums\CandidateSort;
use Modules\Candidates\Enums\CandidateStatus;
use Modules\Candidates\Enums\WorkflowStatus;
use Modules\Shared\Enums\SortOrder;
use Spatie\LaravelData\Attributes\Validation\Between;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Data;

final class CandidateFiltersData extends Data
{
    public function __construct(
        public ?CandidateStatus $status = null,
        public ?WorkflowStatus $workflow_status = null,
        public ?CandidateCategory $category = null,
        #[Min(1)]
        public ?int $source_id = null,
        #[Between(0, 100)]
        public ?int $min_score = null,
        #[Between(0, 100)]
        public ?int $max_score = null,
        public CandidateSort $sort = CandidateSort::TotalScore,
        public SortOrder $order = SortOrder::Desc,
        #[Min(1), Max(10000)]
        public int $page = 1,
        #[Between(1, 100)]
        public int $page_size = 25,
    ) {}
}
