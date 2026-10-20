<?php

namespace Modules\Pipeline\Exceptions;

use Modules\Shared\Exceptions\ApiException;

final class JobInputException extends ApiException
{
    public function __construct(string $message, int $status = 409)
    {
        parent::__construct($message, $status, plain: true);
    }
}
