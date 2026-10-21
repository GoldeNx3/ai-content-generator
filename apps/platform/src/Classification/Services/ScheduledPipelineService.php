<?php

namespace Modules\Classification\Services;

use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Modules\Classification\Queries\UnclassifiedCandidatesQuery;
use Modules\Classification\Queries\WorkspacesWithPendingClassificationQuery;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Sources\Data\FetchResultData;
use Modules\Sources\Services\IngestionService;
use Ramsey\Uuid\Uuid;

final class ScheduledPipelineService
{
    private const NAMESPACE = '6ba7b811-9dad-11d1-80b4-00c04fd430c8';

    public function __construct(
        private readonly IngestionService $ingestion,
        private readonly WorkspacesWithPendingClassificationQuery $workspaces,
        private readonly UnclassifiedCandidatesQuery $unclassified,
        private readonly EnqueueService $enqueue,
    ) {}

    public function run(): array
    {
        $fetched = $this->ingestion->fetchAllActive(null);
        $enqueued = config('content.ai.openai_api_key') === '' ? 0 : $this->classify();

        return ['fetch' => $fetched, 'enqueued' => $enqueued];
    }

    private function classify(): int
    {
        $enqueued = 0;
        foreach ($this->workspaces->execute() as $workspaceId) {
            $ids = $this->unclassified->execute($workspaceId, config('content.ingestion.classify_batch_limit'), withoutClassifyHistory: true);
            foreach ($ids as $candidateId) {
                try {
                    $key = Uuid::uuid5(self::NAMESPACE, "scheduled-classify:{$candidateId}")->toString();
                    $this->enqueue->enqueue(JobKind::Classify, $candidateId, [], $key);
                    $enqueued++;
                } catch (JobConflictException) {
                    continue;
                } catch (JobInputException $exception) {
                    if ($exception->status !== 402) {
                        throw $exception;
                    }
                    Log::info('Scheduler: workspace over AI budget, skipping classification', ['workspace_id' => $workspaceId]);
                    break;
                }
            }
        }

        return $enqueued;
    }
}
