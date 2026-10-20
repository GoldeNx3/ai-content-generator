<?php

namespace Modules\Sources\Commands;

use Modules\Sources\Models\Source;

final class CreateSourceCommand
{
    public function execute(int $workspaceId, string $name, string $url, string $type, bool $active): Source
    {
        return Source::query()->create([
            'workspace_id' => $workspaceId, 'name' => $name, 'url' => $url, 'type' => $type, 'active' => $active,
        ]);
    }
}
