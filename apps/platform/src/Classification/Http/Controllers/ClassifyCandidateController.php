<?php

namespace Modules\Classification\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Candidates\Models\Candidate;
use Modules\Classification\Services\ClassificationService;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class ClassifyCandidateController
{
    public function __construct(private readonly ClassificationService $classification) {}

    #[Post('candidates/{candidate}/classify')]
    public function __invoke(Candidate $candidate, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->classification->classify($candidate, IdempotencyKey::from($request)));
    }
}
