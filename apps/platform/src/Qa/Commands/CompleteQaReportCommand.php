<?php

namespace Modules\Qa\Commands;

use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Models\ArticleQa;
use Modules\Qa\Models\ArticleQaIssue;

final class CompleteQaReportCommand
{
    private const ISSUE_FIELDS = ['type', 'severity', 'excerpt', 'reason', 'suggestion', 'section_heading', 'fact_ids', 'source_ids', 'auto_fixable'];

    private const SCORE_FIELDS = [
        'overall_score', 'factual_score', 'source_score', 'style_score', 'structure_score', 'seo_score',
        'supported_claims_count', 'unsupported_claims_count', 'critical_issue_count', 'warning_count', 'qa_passed',
    ];

    public function execute(ArticleQa $report, array $result, CallUsage $usage): void
    {
        ArticleQaIssue::query()->where('article_qa_id', $report->id)->delete();
        foreach ($result['issues'] as $issue) {
            ArticleQaIssue::query()->create([...array_intersect_key($issue, array_flip(self::ISSUE_FIELDS)), 'article_qa_id' => $report->id]);
        }
        $report->update([
            ...array_intersect_key($result, array_flip(self::SCORE_FIELDS)),
            'summary' => $result['summary'], 'claims' => $result['claims'], 'status' => 'completed',
            'llm_model' => $usage->model, 'llm_input_tokens' => $usage->inputTokens, 'llm_output_tokens' => $usage->outputTokens,
            'estimated_cost_usd' => $usage->costUsd,
        ]);
    }
}
