<?php

namespace Modules\WordPress\Support;

use Modules\WordPress\Exceptions\WordPressException;

final class PublicHostGuard
{
    public function curlResolve(string $url): array
    {
        $parts = parse_url($url);
        $host = $parts['host'] ?? '';
        $port = $parts['port'] ?? (($parts['scheme'] ?? 'https') === 'https' ? 443 : 80);
        $addresses = filter_var($host, FILTER_VALIDATE_IP) ? [$host] : $this->resolve($host);
        if ($addresses === []) {
            throw new WordPressException('wordpress_connection', true);
        }
        foreach ($addresses as $address) {
            if (filter_var($address, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) {
                throw new WordPressException('wordpress_connection');
            }
        }

        return [CURLOPT_RESOLVE => ["{$host}:{$port}:".implode(',', $addresses)]];
    }

    private function resolve(string $host): array
    {
        $records = @dns_get_record($host, DNS_A | DNS_AAAA) ?: [];

        return array_values(array_unique(array_filter(array_map(fn ($record) => $record['ip'] ?? $record['ipv6'] ?? null, $records))));
    }
}
