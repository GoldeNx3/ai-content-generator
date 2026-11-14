<?php

namespace Modules\Pipeline\Data;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Spatie\LaravelData\Data;

final class JobData extends Data
{
    public function __construct(
        public string $id,
        public JobKind $kind,
        public ?int $article_id,
        public int $candidate_id,
        public ?string $candidate_title,
        public JobStatus $status,
        public ?string $stage,
        public int $attempt_count,
        public int $max_attempts,
        public CarbonImmutable $available_at,
        public CarbonImmutable $created_at,
        public ?CarbonImmutable $started_at,
        public ?CarbonImmutable $finished_at,
        public ?string $result_type,
        public ?int $result_id,
        public ?string $error_code,
        public ?string $error_message,
        public ?array $result,
        public ?array $error,
        public ?CarbonImmutable $cancel_requested_at = null,
    ) {}

    public static function fromModel(PipelineJob $job, ?string $candidateTitle = null): self
    {
        return new self(
            $job->id, $job->kind, $job->article_id, $job->candidate_id, $candidateTitle, $job->status, $job->stage,
            $job->attempt_count, $job->max_attempts, $job->available_at, $job->created_at->toImmutable(),
            $job->started_at, $job->finished_at, $job->result_type, $job->result_id, $job->error_code, $job->error_message,
            $job->result_id !== null ? ['type' => $job->result_type, 'id' => $job->result_id] : null,
            $job->error_code !== null ? ['code' => $job->error_code, 'message' => $job->error_message] : null,
            $job->cancel_requested_at,
        );
    }
}
