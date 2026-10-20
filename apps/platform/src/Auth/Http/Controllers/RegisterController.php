<?php

namespace Modules\Auth\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Auth\Data\RegisterData;
use Modules\Auth\Services\AuthService;
use Spatie\RouteAttributes\Attributes\Post;

final class RegisterController
{
    public function __construct(private readonly AuthService $auth) {}

    #[Post('auth/register')]
    public function __invoke(RegisterData $data, Request $request): JsonResponse
    {
        return response()->json($this->auth->register($data, $request), 201);
    }
}
