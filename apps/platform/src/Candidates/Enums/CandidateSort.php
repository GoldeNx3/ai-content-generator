<?php

namespace Modules\Candidates\Enums;

enum CandidateSort: string
{
    case TotalScore = 'total_score';
    case CreatedAt = 'created_at';
    case OriginalPublishedAt = 'original_published_at';
}
