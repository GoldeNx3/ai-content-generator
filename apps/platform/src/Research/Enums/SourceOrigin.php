<?php

namespace Modules\Research\Enums;

enum SourceOrigin: string
{
    case Original = 'original';
    case Search = 'search';
    case Manual = 'manual';
    case Sibling = 'sibling';
}
