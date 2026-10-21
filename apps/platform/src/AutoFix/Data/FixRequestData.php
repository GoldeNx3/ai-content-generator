<?php

namespace Modules\AutoFix\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class FixRequestData extends Data
{
    public function __construct(
        #[Max(100)]
        public ?array $issue_ids = null,
    ) {}

    public static function rules(): array
    {
        return ['issue_ids.*' => ['integer', 'min:1', 'distinct']];
    }
}
