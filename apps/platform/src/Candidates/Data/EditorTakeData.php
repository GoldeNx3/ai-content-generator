<?php

namespace Modules\Candidates\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class EditorTakeData extends Data
{
    public function __construct(
        #[Max(3000)]
        public ?string $editor_take = null,
    ) {}
}
