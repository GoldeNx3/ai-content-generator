<?php

namespace Modules\Classification\Handlers;

use Modules\Classification\Commands\ApplyClassificationCommand;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;

final class ClassifyHandler extends BaseStageHandler
{
    public function __construct(private readonly ApplyClassificationCommand $apply) {}

    public function kind(): JobKind
    {
        return JobKind::Classify;
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $context->stage('classifying');
        $response = $context->ai('classify', 'classify', ['candidate' => $job->payload['candidate_input']]);
        $context->finish(function () use ($job, $response): StageResult {
            $this->apply->execute($job->candidate_id, $job->id, $response['result'], CallUsage::of($response['calls']));

            return new StageResult('candidate', $job->candidate_id);
        });
    }
}
