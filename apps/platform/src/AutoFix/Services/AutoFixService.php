<?php

namespace Modules\AutoFix\Services;

use Illuminate\Support\Collection;
use Modules\Articles\Models\Article;
use Modules\AutoFix\Data\FixData;
use Modules\AutoFix\Models\ArticleFix;
use Modules\AutoFix\Queries\FixesForVersionQuery;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\EnqueueService;

final class AutoFixService
{
    public function __construct(private readonly EnqueueService $enqueue, private readonly FixesForVersionQuery $fixes) {}

    public function fix(Article $article, ?array $issueIds, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::AutoFixArticle, $article->candidate_id, [
            'article_id' => $article->id,
            'issue_ids' => $issueIds === null ? null : array_values(array_unique(array_map('intval', $issueIds))),
        ], $key);
    }

    public function show(ArticleFix $fix): FixData
    {
        return FixData::fromModel($fix->load('issues'));
    }

    public function history(Article $article): Collection
    {
        return $this->fixes->execute($article->id)->map(fn (ArticleFix $fix) => FixData::fromModel($fix));
    }
}
