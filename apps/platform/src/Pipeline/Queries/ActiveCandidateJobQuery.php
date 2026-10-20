<?php

namespace Modules\Pipeline\Queries;

use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class ActiveCandidateJobQuery
{
    public function execute(int $candidateId): ?PipelineJob
    {
        return PipelineJob::query()->where('candidate_id', $candidateId)->whereIn('status', JobStatus::active())->first();
    }
}
