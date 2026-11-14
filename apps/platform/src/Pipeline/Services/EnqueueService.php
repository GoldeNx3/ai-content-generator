<?php

namespace Modules\Pipeline\Services;

use Carbon\CarbonImmutable;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Commands\CreateJobCommand;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\ActiveCandidateJobQuery;
use Modules\Pipeline\Queries\CandidateWorkspaceQuery;
use Modules\Pipeline\Queries\FindJobByKeyQuery;
use Modules\Pipeline\Queries\LockCandidateQuery;
use Modules\Shared\Exceptions\ApiException;
use Modules\Usage\Services\BudgetService;
use Modules\Workspaces\Queries\WorkspacePausedQuery;
use Modules\Workspaces\Services\EditorialProfileService;

final class EnqueueService
{
    public function __construct(
        private readonly FindJobByKeyQuery $byKey,
        private readonly ActiveCandidateJobQuery $activeJob,
        private readonly LockCandidateQuery $lockCandidate,
        private readonly CreateJobCommand $createJob,
        private readonly HandlerRegistry $handlers,
        private readonly BudgetService $budget,
        private readonly WorkspacePausedQuery $paused,
        private readonly CandidateWorkspaceQuery $candidateWorkspace,
        private readonly EditorialProfileService $editorial,
    ) {}

    public function enqueue(JobKind $kind, int $candidateId, array $options = [], ?string $key = null, ?string $retryOf = null): PipelineJob
    {
        $key ??= (string) Str::uuid();
        $hash = $this->requestHash($kind, $candidateId, $options);
        $workspaceId = $this->candidateWorkspace->execute($candidateId) ?? throw new JobInputException('Candidate not found', 404);
        if ($previous = $this->replay($workspaceId, $key, $hash)) {
            return $previous;
        }
        try {
            $job = DB::transaction(function () use ($kind, $candidateId, $options, $key, $hash, $retryOf, $workspaceId): PipelineJob {
                $candidate = $this->lockCandidate->execute($candidateId);
                if ($previous = $this->replay($workspaceId, $key, $hash)) {
                    return $previous;
                }
                if ($active = $this->activeJob->execute($candidateId)) {
                    throw new JobConflictException($active->request_hash === $hash ? 'job_already_active' : 'candidate_busy', $active->id);
                }
                $this->ensureAllowed($kind, $candidate);
                $handler = $this->handlers->for($kind);
                $job = $this->createJob->execute([
                    'workspace_id' => $candidate->workspace_id,
                    'candidate_id' => $candidate->id,
                    'kind' => $kind,
                    'payload' => [...$this->basePayload($candidate, $options), ...$handler->prepare($candidate, $options)],
                    'idempotency_key' => $key,
                    'request_hash' => $hash,
                    'max_attempts' => config('content.jobs.max_attempts'),
                    'available_at' => CarbonImmutable::now(),
                    'retry_of_job_id' => $retryOf,
                ]);
                $handler->created($job);

                return $job;
            });
        } catch (UniqueConstraintViolationException $exception) {
            if ($previous = $this->replay($workspaceId, $key, $hash)) {
                return $previous;
            }
            throw new JobConflictException('candidate_busy');
        }
        if ($job->wasRecentlyCreated) {
            RunPipelineJob::dispatch($job->id, $kind->value)->afterCommit();
        }

        return $job->refresh();
    }

    private function replay(int $workspaceId, string $key, string $hash): ?PipelineJob
    {
        $previous = $this->byKey->execute($workspaceId, $key);
        if ($previous !== null && $previous->request_hash !== $hash) {
            throw new JobConflictException('idempotency_conflict', $previous->id);
        }

        return $previous;
    }

    private function ensureAllowed(JobKind $kind, Candidate $candidate): void
    {
        if ($this->paused->execute($candidate->workspace_id)) {
            throw new ApiException('workspace_paused', 409);
        }
        if ($candidate->isDemo()) {
            return;
        }
        if ($kind->requiresOpenAi() && config('content.ai.openai_api_key') === '') {
            throw new JobInputException('OPENAI_API_KEY is not set', 503);
        }
        if ($kind->isPaid()) {
            $this->budget->ensureAvailable($candidate->workspace_id);
        }
    }

    private function basePayload(Candidate $candidate, array $options): array
    {
        return [
            'payload_version' => 2,
            'options' => $options,
            'demo' => $candidate->isDemo(),
            'candidate_input' => [
                'title' => $candidate->title,
                'summary' => $candidate->summary,
                'source' => $candidate->source->name,
                'published_at' => $candidate->original_published_at?->toIso8601String(),
            ],
            'original_url' => $candidate->external_url,
            'editorial' => $this->editorial->forPayload($candidate->workspace_id),
        ];
    }

    private function requestHash(JobKind $kind, int $candidateId, array $options): string
    {
        return hash('sha256', json_encode([$kind->value, $candidateId, $this->sorted($options)], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
    }

    private function sorted(array $value): array
    {
        if (! array_is_list($value)) {
            ksort($value);
        }

        return array_map(fn ($item) => is_array($item) ? $this->sorted($item) : $item, $value);
    }
}
