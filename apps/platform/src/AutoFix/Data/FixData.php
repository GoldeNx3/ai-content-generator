<?php

namespace Modules\AutoFix\Data;

use Carbon\CarbonImmutable;
use Modules\AutoFix\Models\ArticleFix;
use Spatie\LaravelData\Data;

final class FixData extends Data
{
    public function __construct(
        public int $id,
        public int $source_article_version_id,
        public ?int $result_article_version_id,
        public int $qa_id,
        public ?string $job_id,
        public string $status,
        public int $iteration,
        public int $issues_requested,
        public int $issues_fixed,
        public int $issues_skipped,
        public ?string $summary,
        public ?string $change_ratio,
        public array $warnings,
        public array $changes,
        public ?string $llm_model,
        public ?int $llm_input_tokens,
        public ?int $llm_output_tokens,
        public ?string $estimated_cost_usd,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
        public array $issues,
    ) {}

    public static function fromModel(ArticleFix $fix): self
    {
        return new self(
            $fix->id, $fix->source_article_version_id, $fix->result_article_version_id, $fix->qa_id, $fix->job_id, $fix->status,
            $fix->iteration, $fix->issues_requested, $fix->issues_fixed, $fix->issues_skipped, $fix->summary, $fix->change_ratio,
            $fix->warnings ?? [], $fix->changes ?? [], $fix->llm_model, $fix->llm_input_tokens, $fix->llm_output_tokens,
            $fix->estimated_cost_usd, $fix->created_at->toImmutable(), $fix->updated_at->toImmutable(),
            $fix->issues->map(fn ($issue) => [
                'id' => $issue->id, 'qa_issue_id' => $issue->qa_issue_id, 'status' => $issue->status, 'reason' => $issue->reason,
                'created_at' => $issue->created_at->toIso8601String(),
            ])->all(),
        );
    }
}
