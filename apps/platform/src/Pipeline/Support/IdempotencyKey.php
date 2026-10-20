<?php

namespace Modules\Pipeline\Support;

use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Modules\Shared\Exceptions\ApiException;

final class IdempotencyKey
{
    public static function from(Request $request): ?string
    {
        $key = $request->header('Idempotency-Key');
        if ($key === null || $key === '') {
            return null;
        }
        if (! Str::isUuid($key)) {
            throw ApiException::plain('Idempotency-Key must be a UUID', 422);
        }

        return strtolower($key);
    }
}
