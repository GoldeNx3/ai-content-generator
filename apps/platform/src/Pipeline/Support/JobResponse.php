<?php

namespace Modules\Pipeline\Support;

use Illuminate\Http\JsonResponse;
use Modules\Pipeline\Data\JobData;
use Modules\Pipeline\Models\PipelineJob;

final class JobResponse
{
    public static function accepted(PipelineJob $job): JsonResponse
    {
        return response()->json(JobData::fromModel($job), 202, ['Location' => "/api/jobs/{$job->id}"]);
    }
}
