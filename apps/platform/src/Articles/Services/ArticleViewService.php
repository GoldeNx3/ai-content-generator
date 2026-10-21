<?php

namespace Modules\Articles\Services;

use Illuminate\Support\Collection;
use Modules\Articles\Data\ArticleData;
use Modules\Articles\Data\ArticleQaState;
use Modules\Articles\Data\ArticleSummaryData;
use Modules\Articles\Models\Article;
use Modules\Articles\Support\Lineage;
use Modules\Articles\Queries\ArticleVersionsQuery;
use Modules\Articles\Queries\CompletedFixIterationsQuery;
use Modules\Qa\Queries\LatestQaForArticlesQuery;
use Modules\Qa\Queries\LatestQaQuery;
use Modules\Qa\Support\QaSnapshot;

final class ArticleViewService
{
    public function __construct(
        private readonly ArticleVersionsQuery $versions,
        private readonly LatestQaQuery $latestQa,
        private readonly LatestQaForArticlesQuery $latestQaForArticles,
        private readonly CompletedFixIterationsQuery $fixIterations,
    ) {}

    public function summaries(int $candidateId): Collection
    {
        $articles = $this->versions->execute($candidateId);
        $reports = $this->latestQaForArticles->execute($articles->pluck('id')->all());
        $fixes = $this->fixIterations->execute($articles->pluck('id')->all());
        $byId = $articles->keyBy('id')->all();

        return $articles->map(fn (Article $article) => ArticleSummaryData::fromModel(
            $article, $this->state($article, $reports[$article->id] ?? null, $byId, $fixes),
        ));
    }

    public function details(Article $article): ArticleData
    {
        $versions = $this->versions->execute($article->candidate_id);

        return ArticleData::fromModel($article, $this->state(
            $article,
            $this->latestQa->execute($article->id),
            $versions->keyBy('id')->all(),
            $this->fixIterations->execute($versions->pluck('id')->all()),
        ));
    }

    public function iterationsUsed(Article $article, array $versions, array $fixes): int
    {
        $used = [$article->auto_fix_iteration];
        foreach (Lineage::walk($versions, $article->id) as $id) {
            $used[] = $fixes[$id] ?? 0;
        }

        return max($used);
    }

    private function state(Article $article, ?object $report, array $versions, array $fixes): ArticleQaState
    {
        $matches = QaSnapshot::matches($report, $article);
        $remaining = max(0, config('content.ai.settings.auto_fix_max_iterations') - $this->iterationsUsed($article, $versions, $fixes));

        return new ArticleQaState(
            $report !== null && $report->status === 'completed' && $matches ? $report->overall_score : null,
            $report === null ? 'required' : ($matches ? $report->status : 'stale'),
            $remaining,
        );
    }
}
