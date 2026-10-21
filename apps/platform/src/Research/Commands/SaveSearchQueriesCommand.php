<?php

namespace Modules\Research\Commands;

use Modules\Research\Models\Research;

final class SaveSearchQueriesCommand
{
    public function execute(Research $research, array $queries): void
    {
        $research->update(['search_queries' => $queries]);
    }
}
