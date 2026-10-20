<?php

namespace Modules\Pipeline\Services;

use Illuminate\Support\Collection;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Data\JobAttemptData;
use Modules\Pipeline\Data\JobData;
use Modules\Pipeline\Data\QueueFiltersData;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\CandidateJobsQuery;
use Modules\Pipeline\Queries\JobListQuery;
use Modules\Pipeline\Queries\JobStatsQuery;
use Modules\Shared\Data\PageData;

final class JobService
{
    public function __construct(
        private readonly JobListQuery $list,
        private readonly CandidateJobsQuery $candidateJobs,
        private readonly JobStatsQuery $stats,
        private readonly EnqueueService $enqueue,
    ) {}

    public function list(int $workspaceId, QueueFiltersData $filters): PageData
    {
        [$items, $total] = $this->list->execute($workspaceId, $filters);

        return new PageData(
            $items->map(fn (PipelineJob $job) => JobData::fromModel($job, $job->candidate_title))->all(),
            $total, $filters->page, $filters->page_size,
        );
    }

    public function forCandidate(Candidate $candidate, ?string $status, int $page, int $pageSize): PageData
    {
        [$items, $total] = $this->candidateJobs->execute($candidate->id, $status, $page, $pageSize);

        return new PageData($items->map(fn (PipelineJob $job) => JobData::fromModel($job))->all(), $total, $page, $pageSize);
    }

    public function stats(int $workspaceId): array
    {
        return $this->stats->execute($workspaceId);
    }

    public function attempts(PipelineJob $job): Collection
    {
        return $job->attempts()->get()->map(fn ($attempt) => JobAttemptData::fromModel($attempt));
    }

    public function retry(PipelineJob $job, ?string $key): PipelineJob
    {
        if ($job->status !== JobStatus::Failed) {
            throw new JobConflictException('job_not_failed', $job->id);
        }

        return $this->enqueue->enqueue($job->kind, $job->candidate_id, $job->payload['options'] ?? [], $key, $job->id);
    }
}
