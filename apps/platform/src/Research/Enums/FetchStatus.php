<?php

namespace Modules\Research\Enums;

enum FetchStatus: string
{
    case Pending = 'pending';
    case Success = 'success';
    case Failed = 'failed';
}
