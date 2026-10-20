<?php

namespace Modules\Candidates\Enums;

enum CandidateStatus: string
{
    case Pending = 'pending';
    case Approved = 'approved';
    case Ignored = 'ignored';
}
