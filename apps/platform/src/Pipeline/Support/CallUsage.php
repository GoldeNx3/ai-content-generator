<?php

namespace Modules\Pipeline\Support;

final readonly class CallUsage
{
    public function __construct(
        public ?string $model,
        public int $inputTokens,
        public int $outputTokens,
        public ?string $costUsd,
    ) {}

    public static function of(array $calls): self
    {
        $model = null;
        $input = $output = 0;
        $cost = '0';
        $known = $calls !== [];
        foreach ($calls as $call) {
            $usage = $call['usage'] ?? null;
            if (is_array($usage)) {
                $model = $usage['model'] ?? $model;
                $input += (int) ($usage['input_tokens'] ?? 0);
                $output += (int) ($usage['output_tokens'] ?? 0);
            }
            if (($call['estimated_cost_usd'] ?? null) === null) {
                $known = false;
            } else {
                $cost = bcadd($cost, (string) $call['estimated_cost_usd'], 6);
            }
        }

        return new self($model, $input, $output, $known ? $cost : null);
    }
}
