<?php

namespace Modules\Pipeline\Queries;

use Illuminate\Database\Eloquent\Builder;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class CandidateJobsQuery
{
    public function execute(int $candidateId, ?string $status, int $page, int $pageSize): array
    {
        $query = PipelineJob::query()
            ->where('candidate_id', $candidateId)
            ->when($status === 'active', fn (Builder $q) => $q->whereIn('status', JobStatus::active()))
            ->when($status !== null && $status !== 'active', fn (Builder $q) => $q->where('status', $status));
        $total = (clone $query)->count();

        return [$query->orderByDesc('created_at')->orderByDesc('id')->forPage($page, $pageSize)->get(), $total];
    }
}
