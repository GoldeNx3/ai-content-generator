<?php

namespace Modules\AutoFix\Queries;

use Modules\AutoFix\Models\ArticleFix;

final class FixForJobQuery
{
    public function execute(string $jobId): ?ArticleFix
    {
        return ArticleFix::query()->where('job_id', $jobId)->first();
    }
}
