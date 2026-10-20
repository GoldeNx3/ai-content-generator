<?php

namespace Modules\Sources\Commands;

use Carbon\CarbonImmutable;
use Modules\Sources\Models\Source;

final class MarkSourceFetchedCommand
{
    public function execute(Source $source): void
    {
        $source->forceFill(['last_fetched_at' => CarbonImmutable::now()])->save();
    }
}
