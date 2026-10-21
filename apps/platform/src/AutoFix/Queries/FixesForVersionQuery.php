<?php

namespace Modules\AutoFix\Queries;

use Illuminate\Support\Collection;
use Modules\AutoFix\Models\ArticleFix;

final class FixesForVersionQuery
{
    public function execute(int $articleId): Collection
    {
        return ArticleFix::query()->with('issues')
            ->where(fn ($query) => $query->where('source_article_version_id', $articleId)->orWhere('result_article_version_id', $articleId))
            ->orderByDesc('created_at')->orderByDesc('id')->get();
    }

    public function forJob(string $jobId): ?ArticleFix
    {
        return ArticleFix::query()->where('job_id', $jobId)->first();
    }
}
