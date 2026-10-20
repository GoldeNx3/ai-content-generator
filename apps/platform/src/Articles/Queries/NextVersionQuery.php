<?php

namespace Modules\Articles\Queries;

use Modules\Articles\Models\Article;

final class NextVersionQuery
{
    public function execute(int $candidateId): int
    {
        return ((int) Article::query()->where('candidate_id', $candidateId)->max('version')) + 1;
    }
}
