<?php

namespace Modules\Research\Http\Controllers;

use Modules\Candidates\Models\Candidate;
use Modules\Research\Data\ResearchData;
use Modules\Research\Services\ResearchService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowResearchController
{
    public function __construct(private readonly ResearchService $research) {}

    #[Get('candidates/{candidate}/research')]
    public function __invoke(Candidate $candidate): ResearchData
    {
        return $this->research->show($candidate);
    }
}
