<?php

namespace Modules\Candidates\Http\Controllers;

use Modules\Candidates\Data\CandidateData;
use Modules\Candidates\Data\EditorTakeData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Services\CandidateService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateEditorTakeController
{
    public function __construct(private readonly CandidateService $candidates) {}

    #[Patch('candidates/{candidate}/editor-take')]
    public function __invoke(Candidate $candidate, EditorTakeData $data): CandidateData
    {
        return $this->candidates->updateEditorTake($candidate, $data->editor_take);
    }
}
