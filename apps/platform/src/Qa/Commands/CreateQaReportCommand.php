<?php

namespace Modules\Qa\Commands;

use Modules\Articles\Models\Article;
use Modules\Qa\Models\ArticleQa;
use Modules\Qa\Support\QaSnapshot;

final class CreateQaReportCommand
{
    public function execute(Article $article, string $jobId, array $snapshot): ArticleQa
    {
        $article->update(['qa_passed' => false]);

        return ArticleQa::query()->create([
            'article_id' => $article->id, 'article_version' => $article->version, 'job_id' => $jobId,
            'input_snapshot' => $snapshot, 'input_hash' => QaSnapshot::hash($snapshot), 'status' => 'pending',
            'pass_score' => config('content.ai.settings.qa_pass_score'),
        ]);
    }
}
