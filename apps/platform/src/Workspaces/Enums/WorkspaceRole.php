<?php

namespace Modules\Workspaces\Enums;

enum WorkspaceRole: string
{
    case Owner = 'owner';
    case Member = 'member';
}
