<?php

namespace Modules\WordPress\Queries;

use Modules\WordPress\Models\WordPressPublication;

final class PublicationForCandidateQuery
{
    public function execute(int $candidateId, bool $lock = false): ?WordPressPublication
    {
        return WordPressPublication::query()->where('candidate_id', $candidateId)
            ->when($lock, fn ($query) => $query->lockForUpdate())
            ->first();
    }
}
