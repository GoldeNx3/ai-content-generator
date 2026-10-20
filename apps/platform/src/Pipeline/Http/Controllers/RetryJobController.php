<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobService;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class RetryJobController
{
    public function __construct(private readonly JobService $jobs) {}

    #[Post('jobs/{job}/retry')]
    public function __invoke(PipelineJob $job, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->jobs->retry($job, IdempotencyKey::from($request)));
    }
}
