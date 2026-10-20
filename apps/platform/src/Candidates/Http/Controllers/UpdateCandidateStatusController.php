<?php

namespace Modules\Candidates\Http\Controllers;

use Modules\Candidates\Data\CandidateData;
use Modules\Candidates\Data\StatusUpdateData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\CandidateService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateCandidateStatusController
{
    public function __construct(private readonly CandidateService $candidates) {}

    #[Patch('candidates/{candidate}/status')]
    public function __invoke(Candidate $candidate, StatusUpdateData $data): CandidateData
    {
        return $this->candidates->updateStatus($candidate, $data->status);
    }
}
