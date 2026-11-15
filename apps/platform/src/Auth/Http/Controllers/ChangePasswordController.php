<?php

namespace Modules\Auth\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Modules\Auth\Data\ChangePasswordData;
use Modules\Auth\Services\AuthService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ChangePasswordController
{
    public function __construct(private readonly AuthService $auth) {}

    #[Post('auth/password')]
    public function __invoke(ChangePasswordData $data, Request $request): Response
    {
        $this->auth->changePassword($data, $request);

        return response()->noContent();
    }
}
