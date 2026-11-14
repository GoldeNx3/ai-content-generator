<?php

namespace Modules\Classification\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Log;
use Modules\Classification\Queries\DueAutomationWorkspacesQuery;
use Modules\Classification\Queries\UnclassifiedCandidatesQuery;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Shared\Exceptions\ApiException;
use Modules\Sources\Services\IngestionService;
use Modules\Workspaces\Commands\RecordAutomationRunCommand;
use Modules\Workspaces\Queries\AutomationSettingsQuery;
use Ramsey\Uuid\Uuid;
use Throwable;

final class ScheduledPipelineService
{
    private const NAMESPACE = '6ba7b811-9dad-11d1-80b4-00c04fd430c8';

    public function __construct(
        private readonly IngestionService $ingestion,
        private readonly DueAutomationWorkspacesQuery $due,
        private readonly AutomationSettingsQuery $settings,
        private readonly RecordAutomationRunCommand $recordRun,
        private readonly UnclassifiedCandidatesQuery $unclassified,
        private readonly EnqueueService $enqueue,
    ) {}

    public function runDue(): array
    {
        $total = ['workspaces' => 0, 'new_candidates' => 0, 'enqueued' => 0];
        foreach ($this->due->execute(CarbonImmutable::now()) as $workspaceId) {
            try {
                $result = $this->runWorkspace($workspaceId, automatic: true);
            } catch (Throwable $exception) {
                Log::error('Scheduler: automation run failed', ['workspace_id' => $workspaceId, 'error' => $exception->getMessage()]);

                continue;
            }
            $total['workspaces']++;
            $total['new_candidates'] += $result['new_candidates'];
            $total['enqueued'] += $result['enqueued'];
        }

        return $total;
    }

    public function runWorkspace(int $workspaceId, bool $automatic): array
    {
        $workspace = $this->settings->execute($workspaceId);
        if ($workspace->paused_at !== null) {
            if (! $automatic) {
                throw new ApiException('workspace_paused', 409);
            }
            Log::info('Scheduler: workspace paused before its run, skipping', ['workspace_id' => $workspaceId]);

            return ['new_candidates' => 0, 'enqueued' => 0, 'errors' => 0, 'budget_exceeded' => false];
        }
        $startedAt = CarbonImmutable::now();
        if ($automatic) {
            $this->recordRun->execute($workspaceId, $startedAt, null);
        }
        $fetched = $this->ingestion->fetchAllActive($workspaceId);
        [$enqueued, $budgetExceeded] = ! $automatic || $workspace->auto_classify_enabled
            ? $this->classify($workspaceId, $workspace->auto_classify_batch_limit)
            : [0, false];
        $result = [
            'new_candidates' => $fetched->new_candidates,
            'enqueued' => $enqueued,
            'errors' => $fetched->errors,
            'budget_exceeded' => $budgetExceeded,
        ];
        if ($automatic) {
            $this->recordRun->execute($workspaceId, $startedAt, $result);
        }

        return $result;
    }

    private function classify(int $workspaceId, int $limit): array
    {
        if (config('content.ai.openai_api_key') === '') {
            return [0, false];
        }
        $enqueued = 0;
        foreach ($this->unclassified->execute($workspaceId, $limit, withoutClassifyHistory: true) as $candidateId) {
            try {
                $key = $this->scheduledKey($candidateId);
                $this->enqueue->enqueue(JobKind::Classify, $candidateId, [], $key);
                $enqueued++;
            } catch (JobConflictException) {
                continue;
            } catch (JobInputException $exception) {
                if ($exception->status !== 402) {
                    throw $exception;
                }
                Log::info('Scheduler: workspace over AI budget, skipping classification', ['workspace_id' => $workspaceId]);

                return [$enqueued, true];
            }
        }

        return [$enqueued, false];
    }

    private function scheduledKey(int $candidateId): string
    {
        $hash = hash_hmac('sha256', "scheduled-classify:{$candidateId}", (string) config('app.key'));

        return Uuid::uuid5(self::NAMESPACE, $hash)->toString();
    }
}
