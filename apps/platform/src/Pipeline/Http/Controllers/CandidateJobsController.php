<?php

namespace Modules\Pipeline\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Services\JobService;
use Modules\Shared\Data\PageData;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class CandidateJobsController
{
    public function __construct(private readonly JobService $jobs) {}

    #[Get('candidates/{candidate}/jobs')]
    public function __invoke(Candidate $candidate, Request $request): PageData
    {
        $query = $request->validate([
            'status' => ['nullable', Rule::in(['active', 'queued', 'running', 'retrying', 'succeeded', 'failed'])],
            'page' => ['nullable', 'integer', 'min:1'],
            'page_size' => ['nullable', 'integer', 'between:1,100'],
        ]);

        return $this->jobs->forCandidate($candidate, $query['status'] ?? null, (int) ($query['page'] ?? 1), (int) ($query['page_size'] ?? 25));
    }
}
