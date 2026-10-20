<?php

namespace Modules\Auth\Data;

use Modules\Workspaces\Data\WorkspaceData;
use Spatie\LaravelData\Data;

final class MeData extends Data
{
    public function __construct(
        public UserData $user,
        public WorkspaceData $workspace,
    ) {}
}
