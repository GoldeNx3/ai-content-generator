<?php

namespace Modules\Qa\Queries;

use Modules\Qa\Models\ArticleQa;

final class QaReportForJobQuery
{
    public function execute(string $jobId): ?ArticleQa
    {
        return ArticleQa::query()->where('job_id', $jobId)->first();
    }
}
