<?php

namespace Modules\WordPress\Exceptions;

use Modules\Pipeline\Exceptions\StageFailedException;
use Modules\Pipeline\Support\ErrorMessages;

final class WordPressException extends StageFailedException
{
    public function __construct(string $code, bool $retryable = false, ?float $retryAfter = null, ?array $details = null)
    {
        parent::__construct($code, ErrorMessages::for($code), $retryable, $retryAfter, $details);
    }
}
