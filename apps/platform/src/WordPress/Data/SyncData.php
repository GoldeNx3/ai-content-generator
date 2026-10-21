<?php

namespace Modules\WordPress\Data;

use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Regex;
use Spatie\LaravelData\Data;

final class SyncData extends Data
{
    public function __construct(
        #[In(['draft', 'future', 'publish'])]
        public ?string $status = null,
        public ?string $scheduled_at = null,
        #[Regex('/^[a-f0-9]{64}$/')]
        public ?string $expected_wp_hash = null,
    ) {}

    public static function rules(): array
    {
        return ['scheduled_at' => ['nullable', 'date']];
    }
}
