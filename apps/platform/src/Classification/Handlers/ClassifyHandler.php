<?php

namespace Modules\Classification\Handlers;

use Modules\Candidates\Commands\AssignTopicGroupCommand;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Queries\NearestArticleQuery;
use Modules\Candidates\Queries\NearestTopicQuery;
use Modules\Classification\Commands\ApplyClassificationCommand;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;

final class ClassifyHandler extends BaseStageHandler
{
    public function __construct(
        private readonly ApplyClassificationCommand $apply,
        private readonly AssignTopicGroupCommand $assignGroup,
        private readonly NearestTopicQuery $nearestTopic,
        private readonly NearestArticleQuery $nearestArticle,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::Classify;
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $input = $job->payload['candidate_input'];
        $context->stage('comparing_topics');
        $embedded = $context->ai('embed', 'embed', ['texts' => [trim($input['title']."\n".($input['summary'] ?? ''))]]);
        $vector = $embedded['result']['vectors'][0];
        $threshold = (float) config('content.topics.similarity_threshold');
        $force = (bool) ($job->payload['options']['force'] ?? false);

        $topic = $force ? null : $this->nearestTopic->execute($job->workspace_id, $job->candidate_id, $vector, (int) config('content.topics.window_days'));
        if ($topic !== null && (float) $topic->similarity >= $threshold) {
            $primaryId = (int) ($topic->topic_group_id ?? $topic->id);
            $context->finish(function () use ($job, $vector, $primaryId, $topic, $embedded): StageResult {
                $primary = Candidate::query()->findOrFail($primaryId);
                $this->apply->execute($job->candidate_id, $job->id, [
                    'relevance' => $primary->relevance_score, 'freshness' => $primary->freshness_score,
                    'search_potential' => $primary->search_potential_score, 'commercial_potential' => $primary->commercial_potential_score,
                    'total_score' => $primary->total_score, 'category' => $primary->category?->value,
                    'reason' => sprintf('Ten sam temat co #%d „%s” (podobieństwo %.2f). Ocena przejęta bez ponownej klasyfikacji.',
                        $primary->id, $primary->title, (float) $topic->similarity),
                ], CallUsage::of($embedded['calls']));
                $this->assignGroup->execute($job->candidate_id, $vector, $primaryId, round((float) $topic->similarity, 4));

                return new StageResult('candidate', $job->candidate_id);
            });

            return;
        }

        $article = $this->nearestArticle->execute($job->workspace_id, $vector);
        if ($article !== null && (float) $article->similarity >= $threshold) {
            $input['already_covered'] = ['title' => $article->title, 'article_id' => (int) $article->id, 'similarity' => round((float) $article->similarity, 4)];
        }
        $context->stage('classifying');
        $response = $context->ai('classify', 'classify', ['candidate' => $input, 'editorial' => $job->payload['editorial'] ?? null]);
        $context->finish(function () use ($job, $vector, $response, $embedded): StageResult {
            $this->apply->execute($job->candidate_id, $job->id, $response['result'], CallUsage::of([...$embedded['calls'], ...$response['calls']]));
            $this->assignGroup->execute($job->candidate_id, $vector, null, null);

            return new StageResult('candidate', $job->candidate_id);
        });
    }
}
