<?php

namespace Modules\Pipeline\Http\Controllers;

use Modules\Pipeline\Data\JobData;
use Modules\Pipeline\Models\PipelineJob;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowJobController
{
    #[Get('jobs/{job}')]
    public function __invoke(PipelineJob $job): JobData
    {
        return JobData::fromModel($job);
    }
}
