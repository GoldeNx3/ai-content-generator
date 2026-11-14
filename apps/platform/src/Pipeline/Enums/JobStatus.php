<?php

namespace Modules\Pipeline\Enums;

enum JobStatus: string
{
    case Queued = 'queued';
    case Running = 'running';
    case Retrying = 'retrying';
    case Succeeded = 'succeeded';
    case Failed = 'failed';
    case Cancelled = 'cancelled';

    public static function active(): array
    {
        return [self::Queued->value, self::Running->value, self::Retrying->value];
    }

    public function isActive(): bool
    {
        return in_array($this->value, self::active(), true);
    }
}
