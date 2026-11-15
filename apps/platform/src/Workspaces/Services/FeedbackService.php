<?php

namespace Modules\Workspaces\Services;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Shared\Exceptions\ApiException;
use Modules\Workspaces\Commands\SetSuggestionStatusCommand;
use Modules\Workspaces\Data\EditorialProfileData;
use Modules\Workspaces\Data\EditorialSuggestionData;
use Modules\Workspaces\Models\EditorialSuggestion;
use Modules\Workspaces\Queries\CandidateSuggestionsQuery;

final class FeedbackService
{
    private const LIMITS = ['style_rule' => 30, 'banned_phrase' => 50];

    public function __construct(
        private readonly EnqueueService $enqueue,
        private readonly CandidateSuggestionsQuery $suggestions,
        private readonly SetSuggestionStatusCommand $setStatus,
        private readonly EditorialProfileService $profiles,
    ) {}

    public function request(Candidate $candidate, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::LearnFeedback, $candidate->id, [], $key);
    }

    public function list(int $candidateId): array
    {
        return array_map(EditorialSuggestionData::fromModel(...), $this->suggestions->execute($candidateId));
    }

    public function accept(EditorialSuggestion $suggestion): EditorialSuggestionData
    {
        return DB::transaction(function () use ($suggestion): EditorialSuggestionData {
            $profile = $this->profiles->show($suggestion->workspace_id);
            $field = $suggestion->kind === 'style_rule' ? 'style_rules' : 'banned_phrases';
            $items = $profile->{$field};
            $known = array_map(fn (string $item) => mb_strtolower(trim($item)), $items);
            if (! in_array(mb_strtolower(trim($suggestion->text)), $known, true)) {
                if (count($items) >= self::LIMITS[$suggestion->kind]) {
                    throw new ApiException('editorial_profile_full', 409);
                }
                $values = $profile->toArray();
                $values[$field] = [...$items, $suggestion->text];
                $this->profiles->update($suggestion->workspace_id, EditorialProfileData::from($values));
            }

            return EditorialSuggestionData::fromModel($this->setStatus->execute($suggestion, 'accepted'));
        });
    }

    public function dismiss(EditorialSuggestion $suggestion): EditorialSuggestionData
    {
        return EditorialSuggestionData::fromModel($this->setStatus->execute($suggestion, 'dismissed'));
    }
}
