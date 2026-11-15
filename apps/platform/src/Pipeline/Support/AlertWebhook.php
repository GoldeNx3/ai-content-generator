<?php

namespace Modules\Pipeline\Support;

use Illuminate\Support\Facades\Http;
use Throwable;

final class AlertWebhook
{
    public function enabled(): bool
    {
        return (string) config('content.alerts.webhook_url') !== '';
    }

    public function send(string $text): bool
    {
        $url = (string) config('content.alerts.webhook_url');
        $discord = str_contains((string) parse_url($url, PHP_URL_HOST), 'discord');
        try {
            return Http::timeout(5)->post($url, $discord ? ['content' => $text] : ['text' => $text])->successful();
        } catch (Throwable $exception) {
            report($exception);

            return false;
        }
    }
}
