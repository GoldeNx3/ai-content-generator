<?php

namespace Tests\Feature\Ai;

use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Process;
use Modules\Ai\Exceptions\AiTaskException;
use Modules\Ai\Services\AiRunner;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class AiRunnerTest extends TestCase
{
    #[Test]
    public function a_crashed_ai_process_keeps_its_traceback_in_the_log_and_out_of_the_panel(): void
    {
        $traceback = "Traceback (most recent call last):\n  File \"/srv/ai/ai/runtime.py\", line 19\nMemoryError";
        Process::fake(['*' => Process::result(output: '', errorOutput: $traceback, exitCode: 137)]);
        Log::spy();

        try {
            app(AiRunner::class)->run('classify', []);
            $this->fail('Expected AiTaskException');
        } catch (AiTaskException $exception) {
            $this->assertSame('ai_process_failed', $exception->errorCode);
            $this->assertTrue($exception->retryable);
            $this->assertSame('Proces AI zakończył się błędem.', $exception->getMessage());
        }

        Log::shouldHaveReceived('error')->withArgs(fn (string $message, array $context) => str_contains($context['stderr'] ?? '', 'MemoryError')
            && ($context['task'] ?? null) === 'classify')->once();
    }
}
