<?php

namespace Modules\Auth\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Auth\Data\LoginData;
use Modules\Auth\Services\AuthService;
use Spatie\RouteAttributes\Attributes\Post;

final class LoginController
{
    public function __construct(private readonly AuthService $auth) {}

    #[Post('auth/login')]
    public function __invoke(LoginData $data, Request $request): JsonResponse
    {
        return response()->json($this->auth->login($data, $request));
    }
}
