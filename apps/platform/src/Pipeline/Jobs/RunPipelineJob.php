<?php

namespace Modules\Pipeline\Jobs;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Modules\Pipeline\Services\JobRunner;
use Throwable;

final class RunPipelineJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable;

    public int $tries = 1;

    public int $timeout;

    public bool $failOnTimeout = true;

    public function __construct(public readonly string $jobId, string $kind)
    {
        $this->timeout = (int) config("content.jobs.timeouts.{$kind}", 900) + 30;
        $this->onQueue('pipeline');
    }

    public function handle(JobRunner $runner): void
    {
        $runner->run($this->jobId);
    }

    public function failed(?Throwable $exception): void
    {
        app(JobRunner::class)->interrupted($this->jobId);
    }
}
