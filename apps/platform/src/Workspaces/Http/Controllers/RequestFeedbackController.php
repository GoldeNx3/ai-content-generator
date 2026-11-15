<?php

namespace Modules\Workspaces\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Modules\Workspaces\Services\FeedbackService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class RequestFeedbackController
{
    public function __construct(private readonly FeedbackService $feedback) {}

    #[Post('candidates/{candidate}/feedback')]
    public function __invoke(Candidate $candidate, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->feedback->request($candidate, IdempotencyKey::from($request)));
    }
}
