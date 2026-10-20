<?php

namespace Modules\Qa\Handlers;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Articles\Queries\ArticleVersionsQuery;
use Modules\Articles\Queries\CompletedFixIterationsQuery;
use Modules\Articles\Services\ArticleViewService;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Commands\QaReportCommand;
use Modules\Qa\Queries\QaReportForJobQuery;
use Modules\Qa\Support\QaSnapshot;
use Modules\Research\Queries\ResearchForCandidateQuery;

final class QaHandler extends BaseStageHandler
{
    public function __construct(
        private readonly QaReportCommand $reports,
        private readonly QaReportForJobQuery $reportForJob,
        private readonly ResearchForCandidateQuery $researchFor,
        private readonly ArticleViewService $views,
        private readonly ArticleVersionsQuery $versions,
        private readonly CompletedFixIterationsQuery $fixIterations,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::QaArticle;
    }

    public function prepare(Candidate $candidate, array $options): array
    {
        $article = Article::query()->whereKey($options['article_id'] ?? 0)->lockForUpdate()->first()
            ?? throw new JobInputException('Article not found', 404);
        if ($article->candidate_id !== $candidate->id) {
            throw new JobInputException('Article belongs to another candidate');
        }
        $research = $this->researchFor->execute($candidate->id, false);
        if ($research !== null && $article->research_id !== null && $research->id !== $article->research_id) {
            throw new JobInputException('Article research does not belong to candidate');
        }

        return ['qa_context' => QaSnapshot::build($article)];
    }

    public function created(PipelineJob $job): void
    {
        $article = Article::query()->findOrFail($job->payload['options']['article_id']);
        $job->update(['article_id' => $article->id]);
        $this->reports->createPending($article, $job->id, $job->payload['qa_context']);
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $report = $this->reportForJob->execute($job->id) ?? throw new JobInputException('QA report not found', 404);
        $context->transaction(fn () => $report->update(['status' => 'running']));
        $context->stage('validating_references');
        $evaluation = $context->ai('evaluate', 'qa.evaluate', [
            'snapshot' => $report->input_snapshot,
            'pass_score' => $report->pass_score,
        ]);
        $context->stage('validating_qa');
        $context->finish(function () use ($job, $report, $evaluation): StageResult {
            $this->reports->complete($report, $evaluation['result'], CallUsage::of($evaluation['calls']));
            $this->applyToArticle(Article::query()->whereKey($job->article_id)->lockForUpdate()->firstOrFail(), $report->refresh());

            return new StageResult('article_qa', $report->id);
        });
    }

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void
    {
        $this->reports->status($job->id, $final ? 'failed' : 'pending');
    }

    private function applyToArticle(Article $article, $report): void
    {
        $passed = (bool) $report->qa_passed && QaSnapshot::matches($report, $article);
        $status = $article->status;
        if (! in_array($status, [ArticleStatus::Superseded, ArticleStatus::Rejected], true)) {
            if ($passed) {
                $status = $status === ArticleStatus::Approved ? $status : ArticleStatus::ReadyForApproval;
            } else {
                $versions = $this->versions->execute($article->candidate_id)->keyBy('id')->all();
                $used = $this->views->iterationsUsed($article, $versions, $this->fixIterations->execute(array_keys($versions)));
                $status = $used >= config('content.ai.settings.auto_fix_max_iterations') ? ArticleStatus::ManualReviewRequired : ArticleStatus::NeedsChanges;
            }
        }
        $article->update(['qa_passed' => $passed, 'status' => $status]);
    }
}
