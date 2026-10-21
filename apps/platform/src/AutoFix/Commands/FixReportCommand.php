<?php

namespace Modules\AutoFix\Commands;

use Modules\AutoFix\Models\ArticleFix;
use Modules\AutoFix\Models\ArticleFixIssue;
use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Support\QaSnapshot;

final class FixReportCommand
{
    public function createPending(int $articleId, string $jobId, array $context): ArticleFix
    {
        return ArticleFix::query()->create([
            'source_article_version_id' => $articleId, 'qa_id' => $context['qa_id'], 'job_id' => $jobId,
            'input_snapshot' => $context, 'input_hash' => QaSnapshot::hash($context), 'iteration' => $context['iteration'],
            'issues_requested' => count($context['issues']), 'status' => 'pending',
        ]);
    }

    public function status(ArticleFix $fix, string $status): void
    {
        $fix->update(['status' => $status]);
    }

    public function fail(ArticleFix $fix, string $status, string $reason): void
    {
        $fix->update(['status' => $status]);
        if ($status === 'failed' && ! $fix->issues()->exists()) {
            foreach ($fix->input_snapshot['issues'] ?? [] as $issue) {
                ArticleFixIssue::query()->create(['article_fix_id' => $fix->id, 'qa_issue_id' => $issue['id'], 'status' => 'failed', 'reason' => $reason]);
            }
        }
    }

    public function complete(ArticleFix $fix, array $result, CallUsage $usage, ?int $resultVersionId): void
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
