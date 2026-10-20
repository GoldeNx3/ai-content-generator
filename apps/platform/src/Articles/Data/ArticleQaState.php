<?php

namespace Modules\Articles\Data;

final readonly class ArticleQaState
{
    public function __construct(
        public ?int $qaScore,
        public string $qaStatus,
        public int $autoFixIterationsRemaining,
    ) {}
}
