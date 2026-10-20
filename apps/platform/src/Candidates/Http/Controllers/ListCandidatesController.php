<?php

namespace Modules\Candidates\Http\Controllers;

use Modules\Candidates\Data\CandidateFiltersData;
use Modules\Candidates\Services\CandidateService;
use Modules\Shared\Data\PageData;
use Modules\Workspaces\Services\CurrentWorkspace;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ListCandidatesController
{
    public function __construct(private readonly CandidateService $candidates, private readonly CurrentWorkspace $workspace) {}

    #[Get('candidates')]
    public function __invoke(CandidateFiltersData $filters): PageData
    {
        return $this->candidates->search($this->workspace->id(), $filters);
    }
}
