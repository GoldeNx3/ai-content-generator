<?php

namespace Modules\Qa\Commands;

use Modules\Qa\Models\ArticleQa;

final class SetQaReportStatusCommand
{
    public function execute(string $jobId, string $status): void
    {
        ArticleQa::query()->where('job_id', $jobId)->update(['status' => $status]);
    }
}
