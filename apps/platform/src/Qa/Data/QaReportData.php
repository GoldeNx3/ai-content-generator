<?php

namespace Modules\Qa\Data;

use Carbon\CarbonImmutable;
use Modules\Qa\Models\ArticleQa;
use Spatie\LaravelData\Data;

final class QaReportData extends Data
{
    public function __construct(
        public int $id,
        public int $article_id,
        public int $article_version,
        public ?string $job_id,
        public string $status,
        public ?int $overall_score,
        public ?int $factual_score,
        public ?int $source_score,
        public ?int $style_score,
        public ?int $structure_score,
        public ?int $seo_score,
        public int $supported_claims_count,
        public int $unsupported_claims_count,
        public int $critical_issue_count,
        public int $warning_count,
        public ?string $summary,
        public ?string $llm_model,
        public ?int $llm_input_tokens,
        public ?int $llm_output_tokens,
        public ?string $estimated_cost_usd,
        public bool $qa_passed,
        public int $pass_score,
        public bool $is_stale,
        public array $issues,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
    ) {}

    public static function fromModel(ArticleQa $report, bool $stale, bool $passed): self
    {
        return new self(
            $report->id, $report->article_id, $report->article_version, $report->job_id, $report->status,
            $report->overall_score, $report->factual_score, $report->source_score, $report->style_score,
            $report->structure_score, $report->seo_score, $report->supported_claims_count, $report->unsupported_claims_count,
            $report->critical_issue_count, $report->warning_count, $report->summary, $report->llm_model,
            $report->llm_input_tokens, $report->llm_output_tokens, $report->estimated_cost_usd, $passed,
            $report->pass_score, $stale, $report->issues->map(fn ($issue) => QaIssueData::fromModel($issue))->all(),
            $report->created_at->toImmutable(), $report->updated_at->toImmutable(),
        );
    }
}
