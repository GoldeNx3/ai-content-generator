<?php

namespace Modules\Pipeline\Commands;

use Modules\Pipeline\Models\PipelineJob;

final class SaveJobCheckpointCommand
{
    public function execute(PipelineJob $job, string $key, mixed $value): void
    {
        $job->forceFill(['checkpoints' => [...($job->checkpoints ?? []), $key => $value]])->save();
    }
}
