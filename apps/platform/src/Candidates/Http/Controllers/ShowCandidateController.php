<?php

namespace Modules\Candidates\Http\Controllers;

use Modules\Candidates\Data\CandidateData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\CandidateService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowCandidateController
{
    public function __construct(private readonly CandidateService $candidates) {}

    #[Get('candidates/{candidate}')]
    public function __invoke(Candidate $candidate): CandidateData
    {
        return $this->candidates->details($candidate);
    }
}
