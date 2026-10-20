<?php

namespace Modules\Shared\Exceptions;

use Illuminate\Http\JsonResponse;
use RuntimeException;

class ApiException extends RuntimeException
{
    public function __construct(
        public readonly string $errorCode,
        public readonly int $status = 400,
        public readonly array $context = [],
        public readonly bool $plain = false,
    ) {
        parent::__construct($errorCode);
    }

    public static function plain(string $message, int $status): self
    {
        return new self($message, $status, plain: true);
    }

    public function render(): JsonResponse
    {
        $detail = $this->plain ? $this->errorCode : ['code' => $this->errorCode, ...$this->context];

        return response()->json(['detail' => $detail], $this->status);
    }
}
