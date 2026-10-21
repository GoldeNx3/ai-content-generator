<?php

namespace Modules\AutoFix\Commands;

use Modules\AutoFix\Models\ArticleFix;
use Modules\Qa\Support\QaSnapshot;

final class CreateFixReportCommand
{
    public function execute(int $articleId, string $jobId, array $context): ArticleFix
    {
        return ArticleFix::query()->create([
            'source_article_version_id' => $articleId, 'qa_id' => $context['qa_id'], 'job_id' => $jobId,
            'input_snapshot' => $context, 'input_hash' => QaSnapshot::hash($context), 'iteration' => $context['iteration'],
            'issues_requested' => count($context['issues']), 'status' => 'pending',
        ]);
    }
}
