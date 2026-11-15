<?php

namespace Modules\Workspaces\Commands;

use Modules\Workspaces\Models\EditorialSuggestion;

final class StoreSuggestionsCommand
{
    public function execute(int $workspaceId, int $candidateId, string $jobId, array $suggestions): void
    {
        foreach ($suggestions as $suggestion) {
            EditorialSuggestion::query()->create([
                'workspace_id' => $workspaceId, 'candidate_id' => $candidateId, 'job_id' => $jobId,
                'kind' => $suggestion['kind'], 'text' => mb_substr($suggestion['text'], 0, 200), 'why' => mb_substr($suggestion['why'], 0, 300),
            ]);
        }
    }
}
