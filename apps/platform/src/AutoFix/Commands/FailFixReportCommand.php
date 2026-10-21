<?php

namespace Modules\AutoFix\Commands;

use Modules\AutoFix\Models\ArticleFix;
use Modules\AutoFix\Models\ArticleFixIssue;

final class FailFixReportCommand
{
    public function execute(ArticleFix $fix, string $status, string $reason): void
    {
        $fix->update(['status' => $status]);
        if ($status === 'failed' && ! $fix->issues()->exists()) {
            foreach ($fix->input_snapshot['issues'] ?? [] as $issue) {
                ArticleFixIssue::query()->create(['article_fix_id' => $fix->id, 'qa_issue_id' => $issue['id'], 'status' => 'failed', 'reason' => $reason]);
            }
        }
    }
}
