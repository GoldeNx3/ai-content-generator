<?php

namespace Modules\Workspaces\Data;

use Modules\Workspaces\Enums\WorkspaceRole;
use Spatie\LaravelData\Data;

final class WorkspaceData extends Data
{
    public function __construct(
        public int $id,
        public string $name,
        public WorkspaceRole $role,
    ) {}
}
