<?php

namespace Tests\Support;

use Illuminate\Process\PendingProcess;
use Illuminate\Support\Facades\Process;

trait FakesAi
{
    protected array $aiRequests = [];

    protected function fakeAi(array $responses): void
    {
        $this->aiRequests = [];
        Process::fake(function (PendingProcess $process) use ($responses) {
            $request = json_decode($process->input, true);
            $this->aiRequests[] = $request;
            $responses['embed'] ??= fn (array $request) => self::aiOk(['vectors' => array_map(fn (string $text) => self::fakeVector($text), $request['input']['texts']), 'model' => 'text-embedding-3-small']);
            $response = $responses[$request['task']] ?? ['ok' => false, 'error' => ['code' => 'unknown_task', 'message' => 'no fake', 'retryable' => false], 'calls' => []];
            if (is_callable($response)) {
                $response = $response($request);
            }

            return Process::result(json_encode($response));
        });
    }

    protected static function aiOk(array $result, array $calls = []): array
    {
        return ['ok' => true, 'result' => $result, 'calls' => $calls];
    }

    protected static function aiError(string $code, bool $retryable = false, array $calls = []): array
    {
        return ['ok' => false, 'error' => ['code' => $code, 'message' => "Błąd {$code}", 'retryable' => $retryable, 'retry_after' => null], 'calls' => $calls];
    }

    protected static function llmCall(string $stage, string $cost = '0.001000', string $model = 'gpt-test'): array
    {
        return ['stage' => $stage, 'finished' => true, 'usage' => ['model' => $model, 'input_tokens' => 100, 'output_tokens' => 20, 'recorded' => true, 'response_id' => null], 'response_id' => null, 'estimated_cost_usd' => $cost];
    }

    protected static function fakeVector(string $text): array
    {
        $vector = array_fill(0, 16, 0.0);
        $vector[hexdec(substr(hash('sha256', $text), 0, 4)) % 16] = 1.0;

        return $vector;
    }
}
