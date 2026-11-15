<?php

namespace Modules\Workspaces\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Workspaces\Models\EditorialSuggestion;
use Modules\Workspaces\Services\FeedbackService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class AcceptSuggestionController
{
    public function __construct(private readonly FeedbackService $feedback) {}

    #[Post('suggestions/{suggestion}/accept')]
    public function __invoke(EditorialSuggestion $suggestion): JsonResponse
    {
        return response()->json($this->feedback->accept($suggestion));
    }
}
