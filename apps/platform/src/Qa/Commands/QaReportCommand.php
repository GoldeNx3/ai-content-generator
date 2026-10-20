<?php

namespace Modules\Qa\Commands;

use Modules\Articles\Models\Article;
use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Models\ArticleQa;
use Modules\Qa\Models\ArticleQaIssue;
use Modules\Qa\Support\QaSnapshot;

final class QaReportCommand
{
    public function createPending(Article $article, string $jobId, array $snapshot): ArticleQa
    {
        $article->update(['qa_passed' => false]);

        return ArticleQa::query()->create([
            'article_id' => $article->id, 'article_version' => $article->version, 'job_id' => $jobId,
            'input_snapshot' => $snapshot, 'input_hash' => QaSnapshot::hash($snapshot), 'status' => 'pending',
            'pass_score' => config('content.ai.settings.qa_pass_score'),
        ]);
    }

    public function status(string $jobId, string $status): void
    {
        ArticleQa::query()->where('job_id', $jobId)->update(['status' => $status]);
    }

    public function complete(ArticleQa $report, array $result, CallUsage $usage): void
    {
        ArticleQaIssue::query()->where('article_qa_id', $report->id)->delete();
        foreach ($result['issues'] as $issue) {
            ArticleQaIssue::query()->create([...array_intersect_key($issue, array_flip([
                'type', 'severity', 'excerpt', 'reason', 'suggestion', 'section_heading', 'fact_ids', 'source_ids', 'auto_fixable',
            ])), 'article_qa_id' => $report->id]);
        }
        $report->update([
            ...array_intersect_key($result, array_flip([
                'overall_score', 'factual_score', 'source_score', 'style_score', 'structure_score', 'seo_score',
                'supported_claims_count', 'unsupported_claims_count', 'critical_issue_count', 'warning_count', 'qa_passed',
            ])),
            'summary' => $result['summary'],
            'claims' => $result['claims'],
            'status' => 'completed',
            'llm_model' => $usage->model,
            'llm_input_tokens' => $usage->inputTokens,
            'llm_output_tokens' => $usage->outputTokens,
            'estimated_cost_usd' => $usage->costUsd,
        ]);
    }
}
