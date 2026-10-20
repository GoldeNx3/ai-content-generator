<?php

namespace Modules\Research\Enums;

enum ResearchStatus: string
{
    case Pending = 'pending';
    case Running = 'running';
    case Completed = 'completed';
    case Failed = 'failed';
}
