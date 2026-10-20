<?php

namespace Modules\Pipeline\Commands;

use Modules\Pipeline\Models\PipelineJob;

final class CreateJobCommand
{
    public function execute(array $attributes): PipelineJob
    {
        return PipelineJob::query()->create($attributes);
    }
}
