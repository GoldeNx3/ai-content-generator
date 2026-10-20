<?php

namespace Modules\Research\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\Research\Services\ResearchService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class RetryResearchController
{
    public function __construct(private readonly ResearchService $research) {}

    #[Post('candidates/{candidate}/research/retry')]
    public function __invoke(Candidate $candidate, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->research->start($candidate, false, IdempotencyKey::from($request)));
    }
}
