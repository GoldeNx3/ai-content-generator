<?php

namespace Modules\Candidates\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\TopicGroupService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class SimilarTopicsController
{
    public function __construct(private readonly TopicGroupService $groups) {}

    #[Get('candidates/{candidate}/similar')]
    public function __invoke(Candidate $candidate): JsonResponse
    {
        return response()->json($this->groups->similar($candidate));
    }
}
