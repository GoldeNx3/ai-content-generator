<?php

namespace Modules\Workspaces\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Candidates\Models\Candidate;
use Modules\Workspaces\Services\FeedbackService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ListSuggestionsController
{
    public function __construct(private readonly FeedbackService $feedback) {}

    #[Get('candidates/{candidate}/suggestions')]
    public function __invoke(Candidate $candidate): JsonResponse
    {
        return response()->json($this->feedback->list($candidate->id));
    }
}
