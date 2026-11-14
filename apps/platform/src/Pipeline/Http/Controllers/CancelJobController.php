<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Pipeline\Data\JobData;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobCancellationService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class CancelJobController
{
    public function __construct(private readonly JobCancellationService $cancellation) {}

    #[Post('jobs/{job}/cancel')]
    public function __invoke(PipelineJob $job, Request $request): JsonResponse
    {
        $cancelled = $this->cancellation->cancel($job, $request->user()?->id);

        return response()->json(JobData::fromModel($cancelled), $cancelled->status === JobStatus::Running ? 202 : 200);
    }
}
