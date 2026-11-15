<?php

namespace Modules\Candidates\Services;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Commands\JoinTopicGroupCommand;
use Modules\Candidates\Commands\LeaveTopicGroupCommand;
use Modules\Candidates\Data\CandidateData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Queries\FindWorkspaceCandidateQuery;
use Modules\Candidates\Queries\SimilarTopicsQuery;
use Modules\Candidates\Queries\TopicGroupMembersQuery;
use Modules\Pipeline\Queries\ActiveCandidateJobQuery;
use Modules\Pipeline\Queries\LockCandidateQuery;
use Modules\Shared\Exceptions\ApiException;

final class TopicGroupService
{
    private const SIMILAR_LIMIT = 5;

    public function __construct(
        private readonly SimilarTopicsQuery $similar,
        private readonly FindWorkspaceCandidateQuery $find,
        private readonly TopicGroupMembersQuery $members,
        private readonly ActiveCandidateJobQuery $activeJob,
        private readonly LockCandidateQuery $lock,
        private readonly JoinTopicGroupCommand $join,
        private readonly LeaveTopicGroupCommand $leave,
        private readonly CandidateService $candidates,
    ) {}

    public function similar(Candidate $candidate): array
    {
        return $this->similar->execute($candidate->workspace_id, $candidate->id, (int) config('content.topics.window_days'), self::SIMILAR_LIMIT);
    }

    public function join(Candidate $candidate, int $targetId): CandidateData
    {
        $target = $this->find->execute($targetId, $candidate->workspace_id) ?? throw new ApiException('not_found', 404);
        $primary = $target->topic_group_id === null ? $target : $this->find->execute($target->topic_group_id, $candidate->workspace_id);
        if ($primary === null || $primary->id === $candidate->id || $candidate->topic_group_id === $primary->id) {
            throw new ApiException('invalid_group_target', 422);
        }
        if ($primary->total_score === null) {
            throw new ApiException('target_not_classified', 409);
        }
        DB::transaction(function () use ($candidate, $primary): void {
            $this->lock->execute($candidate->id);
            $this->guard($candidate);
            if ($this->members->execute($candidate->workspace_id, $candidate->id, $candidate->id) !== []) {
                throw new ApiException('topic_has_members', 409);
            }
            $this->join->execute($candidate->id, $primary);
        });

        return $this->candidates->details($candidate->refresh());
    }

    public function leave(Candidate $candidate): CandidateData
    {
        DB::transaction(function () use ($candidate): void {
            $locked = $this->lock->execute($candidate->id);
            if ($locked->topic_group_id === null) {
                throw new ApiException('not_grouped', 409);
            }
            $this->guard($locked);
            $this->leave->execute($candidate->id, trim(($locked->llm_reason ?? '').' Odłączono ręcznie od grupy tematu #'.$locked->topic_group_id.'.'));
        });

        return $this->candidates->details($candidate->refresh());
    }

    private function guard(Candidate $candidate): void
    {
        if ($this->activeJob->execute($candidate->id) !== null) {
            throw new ApiException('job_active', 409);
        }
    }
}
