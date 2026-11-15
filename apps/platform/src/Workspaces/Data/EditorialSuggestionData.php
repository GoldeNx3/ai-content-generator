<?php

namespace Modules\Workspaces\Data;

use Carbon\CarbonImmutable;
use Modules\Workspaces\Models\EditorialSuggestion;
use Spatie\LaravelData\Data;

final class EditorialSuggestionData extends Data
{
    public function __construct(
        public int $id,
        public int $candidate_id,
        public string $kind,
        public string $text,
        public string $why,
        public string $status,
        public CarbonImmutable $created_at,
    ) {}

    public static function fromModel(EditorialSuggestion $suggestion): self
    {
        return new self($suggestion->id, $suggestion->candidate_id, $suggestion->kind, $suggestion->text, $suggestion->why,
            $suggestion->status, $suggestion->created_at->toImmutable());
    }
}
