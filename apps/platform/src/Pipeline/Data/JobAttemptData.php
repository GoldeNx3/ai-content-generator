<?php

namespace Modules\Pipeline\Data;

use Carbon\CarbonImmutable;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Spatie\LaravelData\Data;

final class JobAttemptData extends Data
{
    public function __construct(
        public int $number,
        public CarbonImmutable $started_at,
        public ?CarbonImmutable $finished_at,
        public string $outcome,
        public ?string $error_code,
        public ?string $error_message,
        public ?string $last_stage,
        public array $llm_calls,
    ) {}

    public static function fromModel(PipelineJobAttempt $attempt): self
    {
        return new self(
            $attempt->number, $attempt->started_at, $attempt->finished_at, $attempt->outcome, $attempt->error_code,
            $attempt->error_message, $attempt->last_stage, $attempt->llm_calls ?? [],
        );
    }
}
