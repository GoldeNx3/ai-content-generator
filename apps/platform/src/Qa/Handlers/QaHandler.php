<?php

namespace Modules\Qa\Handlers;

use Modules\Articles\Commands\UpdateArticleQaStateCommand;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Articles\Queries\ArticleVersionsQuery;
use Modules\Articles\Queries\CompletedFixIterationsQuery;
use Modules\Articles\Services\ArticleViewService;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Commands\AttachJobArticleCommand;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Commands\CompleteQaReportCommand;
use Modules\Qa\Commands\CreateQaReportCommand;
use Modules\Qa\Commands\SetQaReportStatusCommand;
use Modules\Qa\Queries\QaReportForJobQuery;
use Modules\Qa\Support\QaSnapshot;
use Modules\Research\Queries\ResearchForCandidateQuery;

final class QaHandler extends BaseStageHandler
{
    public function __construct(
        private readonly CreateQaReportCommand $createReport,
        private readonly SetQaReportStatusCommand $setReportStatus,
        private readonly CompleteQaReportCommand $completeReport,
        private readonly UpdateArticleQaStateCommand $updateArticleQa,
        private readonly AttachJobArticleCommand $attachArticle,
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
        $this->attachArticle->execute($job, $article->id);
        $this->createReport->execute($article, $job->id, $job->payload['qa_context']);
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $report = $this->reportForJob->execute($job->id) ?? throw new JobInputException('QA report not found', 404);
        $context->transaction(fn () => $this->setReportStatus->execute($job->id, 'running'));
        $context->stage('validating_references');
        $evaluation = $context->ai('evaluate', 'qa.evaluate', [
            'snapshot' => $report->input_snapshot,
            'pass_score' => $report->pass_score,
            'editorial' => $job->payload['editorial'] ?? null,
        ]);
        $context->stage('validating_qa');
        $context->finish(function () use ($job, $report, $evaluation): StageResult {
            $this->completeReport->execute($report, $evaluation['result'], CallUsage::of($evaluation['calls']));
            $this->applyToArticle(Article::query()->whereKey($job->article_id)->lockForUpdate()->firstOrFail(), $report->refresh());

            return new StageResult('article_qa', $report->id);
        });
    }

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void
    {
        $this->setReportStatus->execute($job->id, $final ? 'failed' : 'pending');
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
        $this->updateArticleQa->execute($article, $passed, $status);
    }
}
