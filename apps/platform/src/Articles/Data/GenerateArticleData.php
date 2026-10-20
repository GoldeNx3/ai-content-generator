<?php

namespace Modules\Articles\Data;

use Modules\Candidates\Enums\CandidateCategory;
use Spatie\LaravelData\Attributes\Validation\In;
use Spatie\LaravelData\Attributes\Validation\Max;
use Spatie\LaravelData\Data;

final class GenerateArticleData extends Data
{
    public function __construct(
        #[In(['auto', 'news', 'explainer', 'case_study', 'guide', 'comparison'])]
        public ?string $article_format = null,
        public ?CandidateCategory $article_type = null,
        #[In(['auto', 'short', 'standard', 'long'])]
        public string $length = 'auto',
        #[Max(1000)]
        public ?string $angle = null,
        #[Max(2000)]
        public ?string $instructions = null,
    ) {}

    public function options(): array
    {
        return [
            'article_format' => $this->article_format,
            'article_type' => $this->article_type?->value,
            'length' => $this->length,
            'angle' => $this->angle,
            'instructions' => $this->instructions,
        ];
    }
}
