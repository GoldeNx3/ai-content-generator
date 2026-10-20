<?php

namespace Modules\Pipeline\Contracts;

use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;

interface StageHandler
{
    public function kind(): JobKind;

    public function prepare(Candidate $candidate, array $options): array;

    public function created(PipelineJob $job): void;

    public function run(PipelineJob $job, JobRunContext $context): void;

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void;
}
