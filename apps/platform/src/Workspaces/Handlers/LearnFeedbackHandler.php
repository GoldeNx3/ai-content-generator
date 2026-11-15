<?php

namespace Modules\Workspaces\Handlers;

use Modules\Articles\Models\Article;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Workspaces\Commands\StoreSuggestionsCommand;
use Modules\Workspaces\Queries\FeedbackSourcesQuery;

final class LearnFeedbackHandler extends BaseStageHandler
{
    public function __construct(
        private readonly FeedbackSourcesQuery $sources,
        private readonly StoreSuggestionsCommand $store,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::LearnFeedback;
    }

    public function prepare(Candidate $candidate, array $options): array
    {
        [$edited, $rejections] = $this->sources->execute($candidate->id);
        if ($edited === null && $rejections === []) {
            throw new JobInputException('Ten temat nie ma ręcznie poprawionej wersji ani odrzucenia z powodem.', 422);
        }

        return ['feedback' => ['article_id' => $edited?->id, 'rejections' => $rejections]];
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $candidate = $job->candidate()->firstOrFail();
        $edited = $job->payload['feedback']['article_id'] === null ? null : Article::query()->findOrFail($job->payload['feedback']['article_id']);
        $context->stage('learning_feedback');
        $response = $context->ai('suggest', 'feedback.suggest', [
            'title' => $candidate->title,
            'original' => $edited?->generated_content ?? '',
            'edited' => $edited?->content ?? '',
            'rejections' => $job->payload['feedback']['rejections'],
            'editorial' => $job->payload['editorial'] ?? null,
        ]);
        $context->finish(function () use ($job, $response): StageResult {
            $this->store->execute($job->workspace_id, $job->candidate_id, $job->id, $response['result']['suggestions']);

            return new StageResult('suggestions', $job->candidate_id);
        });
    }
}
