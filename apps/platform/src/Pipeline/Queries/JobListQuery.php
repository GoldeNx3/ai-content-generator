<?php

namespace Modules\Pipeline\Queries;

use Illuminate\Database\Eloquent\Builder;
use Modules\Pipeline\Data\QueueFiltersData;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;

final class JobListQuery
{
    public function execute(int $workspaceId, QueueFiltersData $filters): array
    {
        $query = PipelineJob::query()
            ->where('pipeline_jobs.workspace_id', $workspaceId)
            ->when($filters->status === 'active', fn (Builder $q) => $q->whereIn('pipeline_jobs.status', JobStatus::active()))
            ->when(! in_array($filters->status, ['active', 'all'], true), fn (Builder $q) => $q->where('pipeline_jobs.status', $filters->status))
            ->when($filters->kind, fn (Builder $q) => $q->where('pipeline_jobs.kind', $filters->kind->value))
            ->when($filters->candidate_id !== null, fn (Builder $q) => $q->where('pipeline_jobs.candidate_id', $filters->candidate_id));
        $total = (clone $query)->count();
        $items = $query->select('pipeline_jobs.*', 'candidates.title as candidate_title')
            ->join('candidates', 'candidates.id', '=', 'pipeline_jobs.candidate_id')
            ->orderByDesc('pipeline_jobs.created_at')
            ->orderByDesc('pipeline_jobs.id')
            ->forPage($filters->page, $filters->page_size)
            ->get();

        return [$items, $total];
    }
}
