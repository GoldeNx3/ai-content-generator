<?php

namespace Modules\Candidates\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\TopicGroupService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class LeaveTopicGroupController
{
    public function __construct(private readonly TopicGroupService $groups) {}

    #[Post('candidates/{candidate}/ungroup')]
    public function __invoke(Candidate $candidate): JsonResponse
    {
        return response()->json($this->groups->leave($candidate));
    }
}
