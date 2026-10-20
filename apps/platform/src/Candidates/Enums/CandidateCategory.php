<?php

namespace Modules\Candidates\Enums;

enum CandidateCategory: string
{
    case News = 'news';
    case Guide = 'guide';
    case Comparison = 'comparison';
    case Pricing = 'pricing';
    case Release = 'release';
    case Tool = 'tool';
    case Other = 'other';
}
