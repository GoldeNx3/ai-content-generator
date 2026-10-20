<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class JobAttemptsController
{
    public function __construct(private readonly JobService $jobs) {}

    #[Get('jobs/{job}/attempts')]
    public function __invoke(PipelineJob $job): JsonResponse
    {
        return response()->json($this->jobs->attempts($job));
    }
}
