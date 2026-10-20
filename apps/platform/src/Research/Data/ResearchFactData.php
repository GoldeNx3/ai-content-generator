<?php

namespace Modules\Research\Data;

use Modules\Research\Models\ResearchFact;
use Spatie\LaravelData\Data;

final class ResearchFactData extends Data
{
    public function __construct(
        public int $id,
        public string $claim,
        public string $importance,
        public int $confidence,
        public array $source_ids,
    ) {}

    public static function fromModel(ResearchFact $fact): self
    {
        return new self($fact->id, $fact->claim, $fact->importance, $fact->confidence, $fact->sources->pluck('id')->all());
    }
}
