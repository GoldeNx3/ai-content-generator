<?php

namespace Modules\Ai\Exceptions;

use RuntimeException;

final class AiTaskException extends RuntimeException
{
    public function __construct(
        public readonly string $errorCode,
        string $message,
        public readonly bool $retryable = false,
        public readonly ?float $retryAfter = null,
        public readonly array $calls = [],
    ) {
        parent::__construct($message);
    }
}
