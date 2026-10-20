<?php

namespace Modules\Pipeline\Contracts;

use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Models\PipelineJob;

abstract class BaseStageHandler implements StageHandler
{
    public function prepare(Candidate $candidate, array $options): array
    {
        return [];
    }

    public function created(PipelineJob $job): void {}

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void {}
}
