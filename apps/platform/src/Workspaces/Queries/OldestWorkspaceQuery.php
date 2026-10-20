<?php

namespace Modules\Workspaces\Queries;

use Modules\Workspaces\Models\Workspace;

final class OldestWorkspaceQuery
{
    public function execute(): ?Workspace
    {
        return Workspace::query()->orderBy('created_at')->orderBy('id')->first();
    }
}
