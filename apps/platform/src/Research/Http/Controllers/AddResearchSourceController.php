<?php

namespace Modules\Research\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Candidates\Models\Candidate;
use Modules\Research\Data\ManualSourceData;
use Modules\Research\Services\ResearchService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class AddResearchSourceController
{
    public function __construct(private readonly ResearchService $research) {}

    #[Post('candidates/{candidate}/research/sources')]
    public function __invoke(Candidate $candidate, ManualSourceData $data): JsonResponse
    {
        return response()->json($this->research->addManualSource($candidate, $data->url), 201);
    }
}
