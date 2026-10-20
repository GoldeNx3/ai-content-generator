<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\Workspace;

final class CreateWorkspaceCommand
{
    public function execute(string $name): Workspace
    {
        return Workspace::query()->create(['name' => mb_substr($name, 0, 200)]);
    }
}
