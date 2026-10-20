<?php

namespace Modules\Auth\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Modules\Auth\Services\AuthService;
use Spatie\RouteAttributes\Attributes\Post;

final class LogoutController
{
    public function __construct(private readonly AuthService $auth) {}

    #[Post('auth/logout')]
    public function __invoke(Request $request): Response
    {
        if ($request->user() !== null) {
            $this->auth->logout($request);
        }

        return response()->noContent();
    }
}
