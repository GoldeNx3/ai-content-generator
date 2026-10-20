<?php

namespace Modules\Pipeline\Services;

use Illuminate\Database\QueryException;
use Modules\Ai\Exceptions\AiTaskException;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Exceptions\StageFailedException;
use Modules\Pipeline\Support\ErrorMessages;
use Throwable;

final class FailurePolicy
{
    public function describe(Throwable $exception): array
    {
        return match (true) {
            $exception instanceof AiTaskException => [$exception->errorCode, $exception->getMessage(), $exception->retryable, $exception->retryAfter, null],
            $exception instanceof StageFailedException => [$exception->errorCode, $exception->getMessage() ?: ErrorMessages::for($exception->errorCode), $exception->retryable, $exception->retryAfter, $exception->details],
            $exception instanceof JobInputException => ['invalid_input', $exception->errorCode, false, null, null],
            $exception instanceof QueryException => ['execution_failed', ErrorMessages::for('execution_failed'), true, null, null],
            default => ['execution_failed', ErrorMessages::for('execution_failed'), false, null, null],
        };
    }

    public function delaySeconds(int $attempt, ?float $retryAfter): int
    {
        $delay = ($attempt <= 1 ? 15 : 60) + random_int(0, 5);
        if ($retryAfter !== null) {
            $delay = max($delay, (int) min(900, max(15, $retryAfter)));
        }

        return $delay;
    }
}
