<?php

namespace Modules\Candidates\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Candidates\Data\JoinTopicGroupData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\TopicGroupService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class JoinTopicGroupController
{
    public function __construct(private readonly TopicGroupService $groups) {}

    #[Post('candidates/{candidate}/group')]
    public function __invoke(Candidate $candidate, JoinTopicGroupData $data): JsonResponse
    {
        return response()->json($this->groups->join($candidate, $data->primary_id));
    }
}
