<?php

namespace Modules\Pipeline\Commands;

use Modules\Pipeline\Models\PipelineJob;

final class AttachJobArticleCommand
{
    public function execute(PipelineJob $job, int $articleId): void
    {
        $job->update(['article_id' => $articleId]);
    }
}
