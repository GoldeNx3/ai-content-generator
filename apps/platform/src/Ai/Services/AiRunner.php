<?php

namespace Modules\Ai\Services;

use Illuminate\Support\Facades\Process;
use JsonException;
use Modules\Ai\Data\AiResult;
use Modules\Ai\Exceptions\AiTaskException;

final class AiRunner
{
    public function run(string $task, array $input, bool $demo = false, int $timeoutSeconds = 900): AiResult
    {
        $process = Process::path(config('content.ai.workdir'))
            ->env($this->environment())
            ->input(json_encode(['task' => $task, 'demo' => $demo, 'input' => $input], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE))
            ->timeout($timeoutSeconds)
            ->run([config('content.ai.python'), '-m', 'ai']);

        try {
            $response = json_decode($process->output(), true, flags: JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new AiTaskException('ai_process_failed', mb_substr(trim($process->errorOutput()) ?: 'Proces AI zakończył się bez odpowiedzi.', -2000), retryable: true);
        }
        if (($response['ok'] ?? false) !== true) {
            $error = $response['error'] ?? [];
            throw new AiTaskException(
                (string) ($error['code'] ?? 'execution_failed'),
                (string) ($error['message'] ?? 'Zadanie AI nie powiodło się.'),
                (bool) ($error['retryable'] ?? false),
                isset($error['retry_after']) ? (float) $error['retry_after'] : null,
                $response['calls'] ?? [],
            );
        }

        return new AiResult($response['result'] ?? [], $response['calls'] ?? []);
    }

    private function environment(): array
    {
        $ai = config('content.ai');

        return array_map('strval', array_filter([
            'OPENAI_API_KEY' => $ai['openai_api_key'],
            'TAVILY_API_KEY' => $ai['tavily_api_key'],
            'OPENAI_CLASSIFIER_MODEL' => $ai['models']['classifier'],
            'OPENAI_RESEARCH_MODEL' => $ai['models']['research'],
            'OPENAI_BRIEF_MODEL' => $ai['models']['brief'],
            'OPENAI_WRITER_MODEL' => $ai['models']['writer'],
            'OPENAI_QA_MODEL' => $ai['models']['qa'],
            'OPENAI_AUTO_FIX_MODEL' => $ai['models']['auto_fix'],
            'LLM_PRICING' => json_encode($ai['pricing'], JSON_THROW_ON_ERROR),
            ...array_combine(
                array_map('strtoupper', array_keys($ai['settings'])),
                array_map(fn ($value) => is_bool($value) ? ($value ? 'true' : 'false') : $value, array_values($ai['settings'])),
            ),
            'PYTHONUNBUFFERED' => '1',
        ], fn ($value) => $value !== null && $value !== ''));
    }
}
