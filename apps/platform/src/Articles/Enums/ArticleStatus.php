<?php

namespace Modules\Articles\Enums;

enum ArticleStatus: string
{
    case Draft = 'draft';
    case Review = 'review';
    case Approved = 'approved';
    case Rejected = 'rejected';
    case NeedsChanges = 'needs_changes';
    case ReadyForApproval = 'ready_for_approval';
    case ManualReviewRequired = 'manual_review_required';
    case Superseded = 'superseded';
}
