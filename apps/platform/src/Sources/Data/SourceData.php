<?php

namespace Modules\Sources\Data;

use Carbon\CarbonImmutable;
use Modules\Sources\Models\Source;
use Spatie\LaravelData\Data;

final class SourceData extends Data
{
    public function __construct(
        public int $id,
        public string $name,
        public string $type,
        public string $url,
        public bool $active,
        public ?CarbonImmutable $last_fetched_at,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
    ) {}

    public static function fromModel(Source $source): self
    {
        return new self(
            $source->id, $source->name, $source->type, $source->url, $source->active, $source->last_fetched_at,
            $source->created_at->toImmutable(), $source->updated_at->toImmutable(),
        );
    }
}
