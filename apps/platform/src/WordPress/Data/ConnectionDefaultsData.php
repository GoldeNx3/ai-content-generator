<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Data;
use Spatie\LaravelData\Optional;

final class ConnectionDefaultsData extends Data
{
    public function __construct(
        #[In(['draft', 'future', 'publish'])]
        public string|Optional $default_status,
        #[Min(1)]
        public int|null|Optional $default_author_id,
        #[Min(1)]
        public int|null|Optional $default_category_id,
    ) {}

    public function values(): array
    {
        return array_filter([
            'default_status' => $this->default_status,
            'default_author_id' => $this->default_author_id,
            'default_category_id' => $this->default_category_id,
        ], fn ($value) => ! $value instanceof Optional);
    }
}
