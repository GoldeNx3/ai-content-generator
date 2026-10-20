<?php

namespace Modules\Sources\Commands;

use Modules\Sources\Models\Source;

final class DeleteSourceCommand
{
    public function execute(Source $source): void
    {
        $source->delete();
    }
}
