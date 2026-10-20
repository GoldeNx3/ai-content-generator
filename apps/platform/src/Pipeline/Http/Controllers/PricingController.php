<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class PricingController
{
    #[Get('pricing')]
    public function __invoke(): JsonResponse
    {
        return response()->json([
            'models' => config('content.ai.models'),
            'rates' => config('content.ai.pricing'),
            'source_url' => 'https://developers.openai.com/api/docs/pricing',
            'verified_at' => '2026-10-03',
        ]);
    }
}
