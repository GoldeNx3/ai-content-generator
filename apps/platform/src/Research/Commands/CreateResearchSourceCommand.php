<?php

namespace Modules\Research\Commands;

use Modules\Research\Enums\SourceOrigin;
use Modules\Research\Models\ResearchSource;

final class CreateResearchSourceCommand
{
    public function execute(int $researchId, string $url, SourceOrigin $origin, ?string $title = null): ResearchSource
    {
        return ResearchSource::query()->firstOrCreate(
            ['research_id' => $researchId, 'url' => $url],
            ['origin' => $origin, 'title' => $title],
        );
    }
}
