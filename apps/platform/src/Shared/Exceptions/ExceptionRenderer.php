<?php

namespace Modules\Shared\Exceptions;

use Illuminate\Auth\AuthenticationException;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Http\Exceptions\ThrottleRequestsException;
use Illuminate\Http\JsonResponse;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

final class ExceptionRenderer
{
    public static function register(Exceptions $exceptions): void
    {
        $exceptions->render(fn (ValidationException $e) => self::validation($e));
        $exceptions->render(fn (AuthenticationException $e) => self::detail('not_authenticated', 401));
        $exceptions->render(fn (ModelNotFoundException $e) => self::detail('not_found', 404));
        $exceptions->render(fn (NotFoundHttpException $e) => self::detail('not_found', 404));
        $exceptions->render(fn (AccessDeniedHttpException $e) => self::detail('forbidden', 403));
        $exceptions->render(fn (ThrottleRequestsException $e) => self::detail('too_many_attempts', 429));
    }

    private static function detail(string $code, int $status): JsonResponse
    {
        return response()->json(['detail' => ['code' => $code]], $status);
    }

    private static function validation(ValidationException $exception): JsonResponse
    {
        $detail = [];
        foreach ($exception->errors() as $field => $messages) {
            foreach ($messages as $message) {
                $detail[] = ['loc' => ['body', ...explode('.', $field)], 'msg' => $message, 'type' => 'validation'];
            }
        }

        return response()->json(['detail' => $detail], 422);
    }
}
