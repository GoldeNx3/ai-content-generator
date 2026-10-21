<?php

namespace Modules\AutoFix\Commands;

use Modules\AutoFix\Models\ArticleFix;
use Modules\AutoFix\Models\ArticleFixIssue;
use Modules\Pipeline\Support\CallUsage;

final class CompleteFixReportCommand
{
    public function execute(ArticleFix $fix, array $result, CallUsage $usage, ?int $resultVersionId): void
    {
        foreach ($result['fix_results'] as $issue) {
            ArticleFixIssue::query()->create([
                'article_fix_id' => $fix->id, 'qa_issue_id' => $issue['qa_issue_id'], 'status' => $issue['status'], 'reason' => $issue['reason'],
            ]);
        }
        $fix->update([
            'status' => 'completed', 'summary' => $result['summary'], 'issues_fixed' => $result['issues_fixed'],
            'issues_skipped' => $result['issues_skipped'], 'change_ratio' => $result['change_ratio'],
            'changes' => $result['changes'], 'warnings' => $result['warnings'], 'result_article_version_id' => $resultVersionId,
            'llm_model' => $usage->model, 'llm_input_tokens' => $usage->inputTokens, 'llm_output_tokens' => $usage->outputTokens,
            'estimated_cost_usd' => $usage->costUsd,
        ]);
    }
}
