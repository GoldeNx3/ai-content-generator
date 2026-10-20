<?php

namespace Modules\Qa\Data;

use Carbon\CarbonImmutable;
use Modules\Qa\Models\ArticleQaIssue;
use Spatie\LaravelData\Data;

final class QaIssueData extends Data
{
    public function __construct(
        public int $id,
        public int $article_qa_id,
        public string $type,
        public string $severity,
        public string $excerpt,
        public string $reason,
        public string $suggestion,
        public ?string $section_heading,
        public array $fact_ids,
        public array $source_ids,
        public bool $auto_fixable,
        public CarbonImmutable $created_at,
        public CarbonImmutable $updated_at,
    ) {}

    public static function fromModel(ArticleQaIssue $issue): self
    {
        return new self(
            $issue->id, $issue->article_qa_id, $issue->type, $issue->severity, $issue->excerpt, $issue->reason,
            $issue->suggestion, $issue->section_heading, $issue->fact_ids ?? [], $issue->source_ids ?? [],
            $issue->auto_fixable, $issue->created_at->toImmutable(), $issue->updated_at->toImmutable(),
        );
    }
}
