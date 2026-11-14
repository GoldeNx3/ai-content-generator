<?php

namespace Modules\Classification\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Classification\Services\ClassificationService;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Workspaces\Queries\AutomationSettingsQuery;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware(['auth:sanctum', 'throttle:expensive'])]
final class ClassifyPendingController
{
    public function __construct(
        private readonly ClassificationService $classification,
        private readonly CurrentWorkspace $workspace,
        private readonly AutomationSettingsQuery $settings,
    ) {}

    #[Post('candidates/classify-pending')]
    public function __invoke(Request $request): JsonResponse
    {
        $limit = $request->validate(['limit' => ['nullable', 'integer', 'between:1,200']])['limit'] ?? null;

        return response()->json($this->classification->classifyPending(
            $this->workspace->id(),
            (int) ($limit ?? $this->settings->execute($this->workspace->id())->auto_classify_batch_limit),
            IdempotencyKey::from($request),
        ), 202);
    }
}
