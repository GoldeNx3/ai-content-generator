<?php

namespace Modules\Shared\Support;

final class UrlNormalizer
{
    private const TRACKING_PREFIXES = ['utm_', 'mc_', 'fbclid', 'gclid', 'ref_src'];

    public static function normalize(string $url): string
    {
        $parts = parse_url(trim($url)) ?: [];
        $host = strtolower($parts['host'] ?? '');
        if (str_starts_with($host, 'www.')) {
            $host = substr($host, 4);
        }
        if (isset($parts['port']) && ! in_array($parts['port'], [80, 443], true)) {
            $host .= ':'.$parts['port'];
        }
        $pairs = [];
        foreach (explode('&', $parts['query'] ?? '') as $pair) {
            if ($pair === '') {
                continue;
            }
            $name = strtolower(urldecode(explode('=', $pair, 2)[0]));
            foreach (self::TRACKING_PREFIXES as $prefix) {
                if (str_starts_with($name, $prefix)) {
                    continue 2;
                }
            }
            $pairs[] = $pair;
        }
        $scheme = in_array($parts['scheme'] ?? '', ['http', 'https'], true) ? 'https' : ($parts['scheme'] ?? '');
        $path = rtrim($parts['path'] ?? '', '/');

        return $scheme.'://'.$host.$path.($pairs === [] ? '' : '?'.implode('&', $pairs));
    }
}
