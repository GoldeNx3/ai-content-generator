<?php

namespace Modules\Pipeline\Exceptions;

use RuntimeException;

class StageFailedException extends RuntimeException
{
    public function __construct(
        public readonly string $errorCode,
        string $message,
        public readonly bool $retryable = false,
        public readonly ?float $retryAfter = null,
        public readonly ?array $details = null,
    ) {
        parent::__construct($message);
    }
}
