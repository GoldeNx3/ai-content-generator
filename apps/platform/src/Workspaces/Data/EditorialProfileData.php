<?php

namespace Modules\Workspaces\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class EditorialProfileData extends Data
{
    public function __construct(
        #[Max(500)]
        public string $audience = '',
        #[Max(500)]
        public string $voice = '',
        #[Max(1000)]
        public string $topics_scope = '',
        #[Max(50)]
        public array $banned_phrases = [],
        #[Max(6000)]
        public string $example_post = '',
    ) {}

    public static function rules(): array
    {
        return ['banned_phrases.*' => ['string', 'min:1', 'max:80']];
    }

    public static function fromStored(?array $stored): self
    {
        $stored ??= [];

        return new self(
            (string) ($stored['audience'] ?? ''), (string) ($stored['voice'] ?? ''), (string) ($stored['topics_scope'] ?? ''),
            array_values(array_map('strval', $stored['banned_phrases'] ?? [])), (string) ($stored['example_post'] ?? ''),
        );
    }
}
