<?php

namespace Modules\Workspaces\Data;

use Spatie\LaravelData\Attributes\Validation\Between;
use Spatie\LaravelData\Attributes\Validation\BooleanType;
use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Data;
use Spatie\LaravelData\Optional;

final class UpdateAutomationData extends Data
{
    public const INTERVALS = [15, 30, 60, 120, 360, 720, 1440];

    public function __construct(
        #[BooleanType]
        public bool|Optional $auto_fetch_enabled,
        #[In(self::INTERVALS)]
        public int|Optional $auto_fetch_interval_minutes,
        #[BooleanType]
        public bool|Optional $auto_classify_enabled,
        #[Between(1, 200)]
        public int|Optional $auto_classify_batch_limit,
    ) {}

    public function changes(): array
    {
        return array_filter(
            [
                'auto_fetch_enabled' => $this->auto_fetch_enabled,
                'auto_fetch_interval_minutes' => $this->auto_fetch_interval_minutes,
                'auto_classify_enabled' => $this->auto_classify_enabled,
                'auto_classify_batch_limit' => $this->auto_classify_batch_limit,
            ],
            fn ($value) => ! $value instanceof Optional,
        );
    }
}
