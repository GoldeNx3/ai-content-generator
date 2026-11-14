<?php

namespace Modules\Classification\Services;

use Illuminate\Support\Str;
use Modules\Candidates\Models\Candidate;
use Modules\Classification\Commands\CreateBatchCommand;
use Modules\Classification\Commands\MarkBatchSkippedCommand;
use Modules\Classification\Queries\FindBatchQuery;
use Modules\Classification\Queries\UnclassifiedCandidatesQuery;
use Modules\Pipeline\Data\EnqueuedBatchData;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\FindJobByKeyQuery;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Usage\Services\BudgetService;
use Ramsey\Uuid\Uuid;

final class ClassificationService
{
    public function __construct(
        private readonly EnqueueService $enqueue,
        private readonly UnclassifiedCandidatesQuery $unclassified,
        private readonly CreateBatchCommand $createBatch,
        private readonly MarkBatchSkippedCommand $markSkipped,
        private readonly FindBatchQuery $findBatch,
        private readonly FindJobByKeyQuery $byKey,
        private readonly BudgetService $budget,
    ) {}

    public function classify(Candidate $candidate, ?string $key, bool $force = false): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::Classify, $candidate->id, $force ? ['force' => true] : [], $key);
    }

    public function classifyPending(int $workspaceId, int $limit, ?string $key): EnqueuedBatchData
    {
        $key ??= (string) Str::uuid();
        $hash = hash('sha256', "classify-batch:{$workspaceId}:{$limit}");
        $batch = $this->findBatch->execute($key);
        if ($batch === null) {
            $this->budget->ensureAvailable($workspaceId);
            $batch = $this->createBatch->execute($key, $workspaceId, $hash, $this->unclassified->execute($workspaceId, $limit));
        }
        if ($batch->request_hash !== $hash || $batch->workspace_id !== $workspaceId) {
            throw new JobConflictException('idempotency_conflict');
        }
        $result = new EnqueuedBatchData;
        $ids = $batch->candidate_ids;
        foreach ($ids as $index => $candidateId) {
            if (in_array($candidateId, $this->findBatch->execute($key)->skipped_ids, true)) {
                $result->skipped_busy++;

                continue;
            }
            $childKey = Uuid::uuid5($key, (string) $candidateId)->toString();
            $existed = $this->byKey->execute($workspaceId, $childKey) !== null;
            try {
                $job = $this->enqueue->enqueue(JobKind::Classify, $candidateId, [], $childKey);
                $result->job_ids[] = $job->id;
                $existed ? $result->existing++ : $result->enqueued++;
            } catch (JobInputException $exception) {
                if ($exception->status !== 402) {
                    throw $exception;
                }
                $result->skipped_budget = count($ids) - $index;
                break;
            } catch (JobConflictException) {
                $child = $this->byKey->execute($workspaceId, $childKey);
                if ($child !== null) {
                    $result->job_ids[] = $child->id;
                    $result->existing++;
                } else {
                    $this->markSkipped->execute($key, $candidateId);
                    $result->skipped_busy++;
                }
            }
        }

        return $result;
    }
}
