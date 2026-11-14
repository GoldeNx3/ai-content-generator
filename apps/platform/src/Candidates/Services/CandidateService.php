<?php

namespace Modules\Candidates\Services;

use Modules\Candidates\Commands\UpdateCandidateStatusCommand;
use Modules\Candidates\Data\CandidateData;
use Modules\Candidates\Data\CandidateFiltersData;
use Modules\Candidates\Data\DashboardStatsData;
use Modules\Candidates\Enums\CandidateStatus;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Queries\CandidateDetailsQuery;
use Modules\Candidates\Queries\CandidateSearchQuery;
use Modules\Candidates\Queries\DashboardStatsQuery;
use Modules\Candidates\Queries\TopicGroupMembersQuery;
use Modules\Shared\Data\PageData;

final class CandidateService
{
    public function __construct(
        private readonly CandidateSearchQuery $search,
        private readonly CandidateDetailsQuery $details,
        private readonly DashboardStatsQuery $stats,
        private readonly UpdateCandidateStatusCommand $updateStatus,
        private readonly TopicGroupMembersQuery $groupMembers,
    ) {}

    public function search(int $workspaceId, CandidateFiltersData $filters): PageData
    {
        [$items, $total] = $this->search->execute($workspaceId, $filters);

        return new PageData(
            $items->map(fn (Candidate $candidate) => CandidateData::fromModel($candidate))->all(),
            $total, $filters->page, $filters->page_size,
        );
    }

    public function details(Candidate $candidate): CandidateData
    {
        $data = CandidateData::fromModel($this->details->execute($candidate->id));
        $primaryId = $candidate->topic_group_id ?? $candidate->id;
        $members = $this->groupMembers->execute($candidate->workspace_id, $primaryId, $candidate->id);
        $data->topic_group = $members === [] ? null : ['primary_id' => $primaryId, 'members' => $members];

        return $data;
    }

    public function updateStatus(Candidate $candidate, CandidateStatus $status): CandidateData
    {
        $this->updateStatus->execute($candidate, $status);

        return $this->details($candidate);
    }

    public function stats(int $workspaceId): DashboardStatsData
    {
        return $this->stats->execute($workspaceId);
    }
}
