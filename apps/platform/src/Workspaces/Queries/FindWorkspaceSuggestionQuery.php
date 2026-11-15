<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\EditorialSuggestion;

final class FindWorkspaceSuggestionQuery
{
    public function execute(int $id, int $workspaceId): ?EditorialSuggestion
    {
        return EditorialSuggestion::query()->whereKey($id)->where('workspace_id', $workspaceId)->first();
    }
}
