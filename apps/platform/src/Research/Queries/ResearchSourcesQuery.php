<?php

namespace Modules\Research\Queries;

use Illuminate\Support\Collection;
use Modules\Research\Models\ResearchSource;

final class ResearchSourcesQuery
{
    public function execute(int $researchId, bool $withRawContent = false): Collection
    {
        $query = ResearchSource::query()->where('research_id', $researchId)->orderBy('id');

        return $withRawContent ? $query->get()->each->makeVisible('raw_content') : $query->get();
    }
}
