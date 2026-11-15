<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\EditorialSuggestion;

final class SetSuggestionStatusCommand
{
    public function execute(EditorialSuggestion $suggestion, string $status): EditorialSuggestion
    {
        $suggestion->update(['status' => $status]);

        return $suggestion;
    }
}
