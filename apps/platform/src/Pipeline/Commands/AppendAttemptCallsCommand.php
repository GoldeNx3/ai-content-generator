<?php

namespace Modules\Pipeline\Commands;

use Modules\Pipeline\Models\PipelineJobAttempt;

final class AppendAttemptCallsCommand
{
    public function execute(PipelineJobAttempt $attempt, array $calls): void
    {
        $attempt->forceFill(['llm_calls' => [...($attempt->llm_calls ?? []), ...$calls]])->save();
    }
}
