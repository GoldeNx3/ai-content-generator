<?php

namespace Modules\Articles\Services;

use Illuminate\Support\Facades\DB;
use Modules\Articles\Commands\ArticleStatusCommand;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Queries\LockCandidateQuery;
use Modules\Qa\Queries\LatestQaQuery;
use Modules\Qa\Support\QaSnapshot;

final class ApprovalService
{
    public function __construct(
        private readonly LockCandidateQuery $lockCandidate,
        private readonly LatestQaQuery $latestQa,
        private readonly ArticleStatusCommand $status,
    ) {}

    public function approve(Article $article): Article
    {
        return DB::transaction(function () use ($article): Article {
            $this->lockCandidate->execute($article->candidate_id);
            $article = Article::query()->whereKey($article->id)->lockForUpdate()->firstOrFail();
            if (! in_array($article->status, [ArticleStatus::ReadyForApproval, ArticleStatus::Approved], true) || ! $this->qaPasses($article)) {
                throw new JobInputException('Zatwierdzenie wymaga aktualnego, zaliczonego QA i statusu ready_for_approval.');
            }
            if ($article->status !== ArticleStatus::Approved) {
                $this->status->approve($article);
            }

            return $article->refresh();
        });
    }

    public function reject(Article $article, ?string $reason): Article
    {
        return DB::transaction(function () use ($article, $reason): Article {
            $this->lockCandidate->execute($article->candidate_id);
            $article = Article::query()->whereKey($article->id)->lockForUpdate()->firstOrFail();
            if ($article->status === ArticleStatus::Superseded) {
                throw new JobInputException('Wersja została zastąpiona.');
            }
            $this->status->reject($article, $reason);

            return $article->refresh();
        });
    }

    public function qaPasses(Article $article): bool
    {
        $report = $this->latestQa->execute($article->id);

        return $report !== null
            && $report->status === 'completed'
            && QaSnapshot::matches($report, $article)
            && ($report->overall_score ?? 0) >= config('content.ai.settings.qa_pass_score')
            && ! $report->critical_issue_count
            && ! $report->unsupported_claims_count;
    }
}
