<?php

namespace Modules\Articles\Data;

use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Attributes\Validation\Min;
use Spatie\LaravelData\Data;
use Spatie\LaravelData\Optional;

final class ArticleUpdateData extends Data
{
    public function __construct(
        #[Min(1), Max(300)]
        public string|Optional $title,
        #[Min(1)]
        public string|Optional $lead,
        #[Min(1)]
        public string|Optional $content,
        #[Min(1), Max(300)]
        public string|Optional $meta_title,
        #[Min(1), Max(500)]
        public string|Optional $meta_description,
    ) {}

    public function changes(): array
    {
        $changes = [];
        foreach (['title', 'lead', 'content', 'meta_title', 'meta_description'] as $field) {
            if (! $this->{$field} instanceof Optional) {
                $changes[$field] = $field === 'content' ? $this->{$field} : trim($this->{$field});
            }
        }

        return $changes;
    }
}
