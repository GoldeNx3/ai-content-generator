<?php

namespace Modules\Auth\Http\Controllers;

use Modules\Auth\Data\MeData;
use Modules\Auth\Services\AuthService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class MeController
{
    public function __construct(private readonly AuthService $auth) {}

    #[Get('auth/me')]
    public function __invoke(): MeData
    {
        return $this->auth->me();
    }
}
