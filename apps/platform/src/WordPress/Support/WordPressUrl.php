<?php

namespace Modules\WordPress\Support;

use Modules\Shared\Exceptions\ApiException;

final class WordPressUrl
{
    public static function normalize(?string $value, bool $required = true): ?string
    {
        $value = trim((string) $value);
        if ($value === '') {
            return $required ? throw new ApiException('wordpress_invalid_url', 422) : null;
        }
        $parts = parse_url($value);
        if ($parts === false || ! in_array($parts['scheme'] ?? '', ['http', 'https'], true) || empty($parts['host'])
            || isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment'])) {
            throw new ApiException('wordpress_invalid_url', 422);
        }
        $host = strtolower($parts['host']).(isset($parts['port']) ? ':'.$parts['port'] : '');

        return $parts['scheme'].'://'.$host.rtrim($parts['path'] ?? '', '/');
    }
}
