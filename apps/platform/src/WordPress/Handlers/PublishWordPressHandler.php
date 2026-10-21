<?php

namespace Modules\WordPress\Handlers;

use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;

final class PublishWordPressHandler extends WordPressStage
{
    public function kind(): JobKind
    {
        return JobKind::PublishWordPress;
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        [$article, $connection, $client, $publication] = $this->context($job);
        $profile = $this->profile($context, $article, $publication, false);
        $this->publisher->publish($job, $context, $client, $connection, $article, $publication->refresh(), $profile);
    }
}
