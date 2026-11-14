<?php

namespace Modules\Qa\Services;

use Modules\Articles\Models\Article;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\FindJobByKeyQuery;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Pipeline\Services\JobService;
use Modules\Qa\Data\QaReportData;
use Modules\Qa\Queries\LatestQaQuery;
use Modules\Qa\Support\QaSnapshot;
use Modules\Shared\Exceptions\ApiException;

final class QaService
{
    public function __construct(
        private readonly EnqueueService $enqueue,
        private readonly JobService $jobs,
        private readonly LatestQaQuery $latestQa,
        private readonly FindJobByKeyQuery $byKey,
    ) {}

    public function run(Article $article, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::QaArticle, $article->candidate_id, ['article_id' => $article->id], $key);
    }

    public function latest(Article $article): QaReportData
    {
        $report = $this->latestQa->execute($article->id) ?? throw ApiException::plain('QA report not found', 404);
        $stale = ! QaSnapshot::matches($report, $article);

        return QaReportData::fromModel($report->load('issues'), $stale, (bool) $report->qa_passed && ! $stale && $article->qa_passed);
    }

    public function retry(Article $article, ?string $key): PipelineJob
    {
        $workspaceId = $article->candidate->workspace_id;
        if ($key !== null && ($replay = $this->byKey->execute($workspaceId, $key)) !== null && $replay->retry_of_job_id !== null
            && $replay->kind === JobKind::QaArticle && $replay->candidate_id === $article->candidate_id) {
            return $replay;
        }
        $report = $this->latestQa->execute($article->id);
        if ($report === null || $report->job_id === null) {
            throw ApiException::plain('QA report not found', 404);
        }

        return $this->jobs->retry(PipelineJob::query()->findOrFail($report->job_id), $key);
    }
}
