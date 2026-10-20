<?php

namespace Modules\Sources\Commands;

use Modules\Sources\Models\Source;

final class UpdateSourceCommand
{
    public function execute(Source $source, array $attributes): Source
    {
        $source->update($attributes);

        return $source->refresh();
    }
}
