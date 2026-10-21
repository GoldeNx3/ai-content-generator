<?php

namespace Modules\WordPress\Handlers;

use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;

final class PrepareWordPressHandler extends WordPressStage
{
    public function kind(): JobKind
    {
        return JobKind::PrepareWordPress;
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        [$article, , , $publication] = $this->context($job);
        $this->profile($context, $article, $publication, true);
        $context->finish(function () use ($publication): StageResult {
            $publication->refresh();
            $status = match (true) {
                $publication->wordpress_post_id !== null && $publication->wp_status === 'draft' => 'draft_created',
                $publication->wp_status === 'future' => 'scheduled',
                $publication->wp_status === 'publish' => 'published',
                default => 'not_sent',
            };
            $this->publications->update($publication, ['status' => $status]);

            return new StageResult('wordpress_publication', $publication->id);
        });
    }
}
