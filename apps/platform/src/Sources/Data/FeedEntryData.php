<?php

namespace Modules\Sources\Data;

use Carbon\CarbonImmutable;
use Spatie\LaravelData\Data;

final class FeedEntryData extends Data
{
    public function __construct(
        public string $title,
        public string $url,
        public ?string $summary,
        public ?CarbonImmutable $published_at,
    ) {}
}
