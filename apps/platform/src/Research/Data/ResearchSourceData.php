<?php

namespace Modules\Research\Data;

use Carbon\CarbonImmutable;
use Modules\Research\Enums\FetchStatus;
use Modules\Research\Enums\SourceOrigin;
use Modules\Research\Models\ResearchSource;
use Spatie\LaravelData\Data;

final class ResearchSourceData extends Data
{
    public function __construct(
        public int $id,
        public string $url,
        public SourceOrigin $origin,
        public ?string $title,
        public ?string $publisher,
        public string $source_type,
        public int $source_score,
        public ?CarbonImmutable $published_at,
        public ?string $extracted_content,
        public FetchStatus $fetch_status,
        public ?int $http_status,
        public ?string $error,
        public CarbonImmutable $created_at,
    ) {}

    public static function fromModel(ResearchSource $source): self
    {
        return new self(
            $source->id, $source->url, $source->origin, $source->title, $source->publisher, $source->source_type,
            $source->source_score, $source->published_at, $source->extracted_content, $source->fetch_status,
            $source->http_status, $source->error, $source->created_at->toImmutable(),
        );
    }
}
