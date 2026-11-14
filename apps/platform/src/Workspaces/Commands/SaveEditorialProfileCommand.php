<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\Workspace;

final class SaveEditorialProfileCommand
{
    public function execute(int $workspaceId, array $profile): void
    {
        Workspace::query()->whereKey($workspaceId)->first()?->forceFill(['editorial_profile' => $profile])->save();
    }
}
