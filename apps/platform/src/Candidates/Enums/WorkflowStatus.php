<?php

namespace Modules\Candidates\Enums;

enum WorkflowStatus: string
{
    case Pending = 'pending';
    case Approved = 'approved';
    case Ignored = 'ignored';
    case Draft = 'draft';
    case Published = 'published';
    case Scheduled = 'scheduled';
}
