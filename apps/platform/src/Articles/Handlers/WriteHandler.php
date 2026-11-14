<?php

namespace Modules\Articles\Handlers;

use Modules\Ai\Exceptions\AiTaskException;
use Modules\Articles\Commands\StoreArticleEmbeddingCommand;
use Modules\Articles\Queries\RecentArticlesQuery;
use Modules\Articles\Services\ArticleVersionService;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Exceptions\StageFailedException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;
use Modules\Research\Queries\ResearchForCandidateQuery;
use Modules\WordPress\Queries\PublicationForCandidateQuery;
use Modules\WordPress\Services\BlogMemoryService;

final class WriteHandler extends BaseStageHandler
{
    public function __construct(
        private readonly ResearchForCandidateQuery $researchFor,
        private readonly RecentArticlesQuery $recentArticles,
        private readonly ArticleVersionService $versions,
        private readonly StoreArticleEmbeddingCommand $storeEmbedding,
        private readonly BlogMemoryService $blogMemory,
        private readonly PublicationForCandidateQuery $publication,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::Write;
    }

    public function prepare(Candidate $candidate, array $options): array
    {
        $research = $this->researchFor->execute($candidate->id);
        if ($research === null || $research->status !== ResearchStatus::Completed || $research->facts->isEmpty()) {
            throw new JobInputException('Complete research before generating an article.');
        }

        return ['research_id' => $research->id, 'article_type' => $options['article_type'] ?? $candidate->category?->value ?? 'news',
            'editor_take' => $candidate->editor_take];
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $candidate = $job->candidate()->with('source')->firstOrFail();
        $research = Research::query()->with(['sources', 'facts.sources'])->findOrFail($job->payload['research_id']);
        $request = array_diff_key($job->payload['options'], ['parent_version_id' => true]);

        $this->blogMemory->refreshIfStale($candidate->workspace_id);
        $internalLinks = $this->blogMemory->linkCandidates($candidate->workspace_id, $candidate->title.' '.($research->summary ?? ''),
            $this->publication->execute($candidate->id)?->wordpress_post_id);

        $context->stage('building_brief');
        $brief = $context->ai('brief', 'article.brief', [
            'candidate' => [
                'id' => $candidate->id, 'title' => $candidate->title, 'source' => $candidate->source->name,
                'published_at' => $candidate->original_published_at?->toIso8601String(),
            ],
            'research' => $this->researchPayload($research),
            'article_type' => $job->payload['article_type'],
            'request' => $request,
            'recent_articles' => $this->recentArticles->execute($candidate->workspace_id),
            'editorial' => $job->payload['editorial'] ?? null,
            'editor_take' => array_key_exists('editor_take', $job->payload) ? $job->payload['editor_take'] : $candidate->editor_take,
            'internal_links' => $internalLinks,
            'blog_url' => $this->blogMemory->blogUrl($candidate->workspace_id),
        ]);

        $context->stage('writing');
        $written = $context->ai('write', 'article.write', [
            'candidate_id' => $candidate->id,
            'research_id' => $research->id,
            'article_type' => $job->payload['article_type'],
            'request' => $request,
            'context' => $brief['result']['context'],
            'brief' => $brief['result']['brief'],
            'warnings' => $brief['result']['warnings'],
        ]);

        $embedded = $this->embedArticle($context, $written['result']);

        $context->stage('validating');
        $context->finish(function () use ($job, $research, $brief, $written, $embedded): StageResult {
            $briefUsage = CallUsage::of($brief['calls']);
            $writerUsage = CallUsage::of($written['calls']);
            $total = CallUsage::of([...$brief['calls'], ...$written['calls'], ...$embedded['calls']]);
            $parent = $job->payload['options']['parent_version_id'] ?? null;
            $article = $this->versions->store($job->candidate_id, [
                ...$written['result'],
                'research_id' => $research->id,
                'generation_job_id' => $job->id,
                'parent_version_id' => $parent,
                'created_by' => $parent ? 'regenerated' : 'generated',
                'llm_model' => $writerUsage->model,
                'llm_input_tokens' => $total->inputTokens,
                'llm_output_tokens' => $total->outputTokens,
                'estimated_cost_usd' => $total->costUsd,
                'brief_llm_model' => $briefUsage->model,
                'brief_input_tokens' => $briefUsage->inputTokens,
                'brief_output_tokens' => $briefUsage->outputTokens,
                'brief_cost_usd' => $briefUsage->costUsd,
                'writer_input_tokens' => $writerUsage->inputTokens,
                'writer_output_tokens' => $writerUsage->outputTokens,
                'writer_cost_usd' => $writerUsage->costUsd,
            ]);

            if ($embedded['result'] !== null) {
                $this->storeEmbedding->execute($article->id, $embedded['result']['vectors'][0], $embedded['result']['model'] ?? null);
            }

            return new StageResult('article', $article->id);
        });
    }

    private function researchPayload(Research $research): array
    {
        return [
            'id' => $research->id,
            'summary' => $research->summary,
            'why_it_matters' => $research->why_it_matters,
            'suggested_angle' => $research->suggested_angle,
            'facts' => $research->facts->map(fn ($fact) => [
                'id' => $fact->id, 'claim' => $fact->claim, 'importance' => $fact->importance,
                'confidence' => $fact->confidence, 'basis' => $fact->basis, 'source_ids' => $fact->sources->pluck('id')->all(),
            ])->all(),
            'sources' => $research->sources->map(fn ($source) => [
                'id' => $source->id, 'url' => $source->url, 'origin' => $source->origin->value, 'title' => $source->title,
                'publisher' => $source->publisher, 'source_type' => $source->source_type, 'source_score' => $source->source_score,
                'fetch_status' => $source->fetch_status->value, 'extracted_content' => $source->extracted_content,
            ])->all(),
            'uncertainties' => $research->uncertainties ?? [],
            'conflicts' => $research->conflicts ?? [],
        ];
    }

    private function embedArticle(JobRunContext $context, array $article): array
    {
        try {
            return $context->ai('embed', 'embed', ['texts' => [trim(($article['title'] ?? '')."\n".($article['lead'] ?? ''))]]);
        } catch (AiTaskException $exception) {
            if ($exception->retryable) {
                throw $exception;
            }

            return ['result' => null, 'calls' => $exception->calls];
        } catch (StageFailedException $exception) {
            if ($exception->errorCode !== 'budget_exceeded') {
                throw $exception;
            }

            return ['result' => null, 'calls' => []];
        }
    }
}
