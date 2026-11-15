<?php

namespace Modules\Pipeline\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Cache;
use Modules\Pipeline\Queries\PipelineHealthQuery;
use Modules\Pipeline\Support\AlertWebhook;

final class PipelineHealthService
{
    private const PROBLEMS = [
        'stalled' => 'Kolejka zadań',
        'running' => 'Długo trwające zadania',
        'errors' => 'Błędy dostawcy AI',
    ];

    public function __construct(
        private readonly PipelineHealthQuery $health,
        private readonly AlertWebhook $webhook,
    ) {}

    public function check(): void
    {
        if (! $this->webhook->enabled()) {
            return;
        }
        $now = CarbonImmutable::now();
        $problems = $this->problems($now);
        $repeat = (int) config('content.alerts.repeat_minutes');
        foreach (self::PROBLEMS as $key => $label) {
            $cacheKey = "pipeline-health:{$key}";
            $lastSent = Cache::get($cacheKey);
            if (isset($problems[$key])) {
                if ($lastSent === null || CarbonImmutable::parse($lastSent)->addMinutes($repeat)->lessThanOrEqualTo($now)) {
                    if ($this->webhook->send($problems[$key])) {
                        Cache::forever($cacheKey, $now->toIso8601String());
                    }
                }
            } elseif ($lastSent !== null && $this->webhook->send("✅ Content Engine: {$label} – wróciło do normy.")) {
                Cache::forget($cacheKey);
            }
        }
    }

    private function problems(CarbonImmutable $now): array
    {
        $stall = (int) config('content.alerts.queue_stall_minutes');
        $running = (int) config('content.alerts.running_minutes');
        $window = (int) config('content.alerts.error_window_minutes');
        $state = $this->health->execute($now, $stall, $running, $window);
        $queue = rtrim((string) config('content.frontend_url'), '/').'/queue';
        $problems = [];
        if ($state['stalled'] > 0) {
            $oldest = (int) $state['oldest']->diffInMinutes($now, true);
            $problems['stalled'] = sprintf('⚠️ Content Engine: %d %s w kolejce dłużej niż %d min (najstarsze %d min). Worker kolejki prawdopodobnie nie działa – sprawdź `docker compose ps` i logi `queue`. %s',
                $state['stalled'], self::plural($state['stalled'], 'zadanie czeka', 'zadania czekają', 'zadań czeka'), $stall, $oldest, $queue);
        }
        if ($state['running'] > 0) {
            $problems['running'] = sprintf('⚠️ Content Engine: %d %s dłużej niż %d min. Sprawdź logi `queue` i ewentualnie zatrzymaj zadanie w panelu. %s',
                $state['running'], self::plural($state['running'], 'zadanie trwa', 'zadania trwają', 'zadań trwa'), $running, $queue);
        }
        $errors = array_sum($state['errors']);
        if ($errors >= (int) config('content.alerts.error_burst')) {
            $codes = implode(', ', array_map(fn (string $code, int $count) => "{$code} ×{$count}", array_keys($state['errors']), $state['errors']));
            $problems['errors'] = sprintf('⚠️ Content Engine: %d %s dostawcy AI w ostatnich %d min (%s). Zadania są ponawiane; sprawdź limity i status OpenAI/Tavily. %s',
                $errors, self::plural($errors, 'błąd', 'błędy', 'błędów'), $window, $codes, $queue);
        }

        return $problems;
    }

    private static function plural(int $count, string $one, string $few, string $many): string
    {
        if ($count === 1) {
            return $one;
        }

        return $count % 10 >= 2 && $count % 10 <= 4 && ($count % 100 < 10 || $count % 100 >= 20) ? $few : $many;
    }
}
