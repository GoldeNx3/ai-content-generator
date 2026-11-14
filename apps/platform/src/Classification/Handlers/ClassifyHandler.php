<?php

namespace Modules\Classification\Handlers;

use Modules\Ai\Exceptions\AiTaskException;
use Modules\Candidates\Commands\AssignTopicGroupCommand;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Queries\NearestArticleQuery;
use Modules\Candidates\Queries\NearestTopicQuery;
use Modules\Candidates\Queries\TopicGroupMembersQuery;
use Modules\Classification\Commands\ApplyClassificationCommand;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\WordPress\Queries\SimilarBlogPostQuery;

final class ClassifyHandler extends BaseStageHandler
{
    public function __construct(
        private readonly ApplyClassificationCommand $apply,
        private readonly AssignTopicGroupCommand $assignGroup,
        private readonly NearestTopicQuery $nearestTopic,
        private readonly NearestArticleQuery $nearestArticle,
        private readonly SimilarBlogPostQuery $similarBlogPost,
        private readonly TopicGroupMembersQuery $groupMembers,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::Classify;
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $input = $job->payload['candidate_input'];
        $context->stage('comparing_topics');
        try {
            $embedded = $context->ai('embed', 'embed', ['texts' => [trim($input['title']."\n".($input['summary'] ?? ''))]]);
        } catch (AiTaskException $exception) {
            if ($exception->retryable) {
                throw $exception;
            }
            $embedded = ['result' => null, 'calls' => $exception->calls];
        }
        $vector = $embedded['result']['vectors'][0] ?? null;
        $threshold = (float) config('content.topics.similarity_threshold');
        $force = $vector === null || (bool) ($job->payload['options']['force'] ?? false)
            || $this->groupMembers->execute($job->workspace_id, $job->candidate_id, $job->candidate_id) !== [];

        $topic = $force ? null : $this->nearestTopic->execute($job->workspace_id, $job->candidate_id, $vector, (int) config('content.topics.window_days'));
        $primaryId = $topic === null ? null : (int) ($topic->topic_group_id ?? $topic->id);
        if ($topic !== null && $primaryId !== $job->candidate_id && (float) $topic->similarity >= $threshold) {
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

        $article = $vector === null ? null : $this->nearestArticle->execute($job->workspace_id, $vector);
        if ($article !== null && (float) $article->similarity >= $threshold) {
            $input['already_covered'] = ['title' => $article->title, 'article_id' => (int) $article->id, 'similarity' => round((float) $article->similarity, 4)];
        } elseif (($post = $this->similarBlogPost->execute($job->workspace_id, $input['title'], (float) config('content.topics.blog_title_similarity'))) !== null) {
            $input['already_covered'] = ['title' => $post->title, 'url' => $post->url, 'similarity' => round((float) $post->similarity, 4)];
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
