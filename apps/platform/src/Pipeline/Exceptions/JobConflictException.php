<?php

namespace Modules\Pipeline\Exceptions;

use Modules\Shared\Exceptions\ApiException;

final class JobConflictException extends ApiException
{
    public function __construct(string $code, public readonly ?string $jobId = null)
    {
        parent::__construct($code, 409, ['job_id' => $jobId]);
    }
}
