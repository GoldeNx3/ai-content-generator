<?php

namespace Modules\Pipeline\Commands;

use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;

final class SetJobStageCommand
{
    public function execute(PipelineJob $job, PipelineJobAttempt $attempt, string $stage): void
    {
        $job->forceFill(['stage' => $stage])->save();
        $attempt->forceFill(['last_stage' => $stage])->save();
    }
}
