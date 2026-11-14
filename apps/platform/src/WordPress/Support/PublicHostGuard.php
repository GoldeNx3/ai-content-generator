<?php

namespace Modules\WordPress\Support;

use Modules\Shared\Support\PublicNetwork;
use Modules\WordPress\Exceptions\WordPressException;

final class PublicHostGuard
{
    public function curlResolve(string $url): array
    {
        $parts = parse_url($url);
        $host = $parts['host'] ?? '';
        $port = $parts['port'] ?? (($parts['scheme'] ?? 'https') === 'https' ? 443 : 80);
        $addresses = PublicNetwork::publicAddresses($host);
        if ($addresses === null) {
            throw new WordPressException('wordpress_connection');
        }
        if ($addresses === []) {
            throw new WordPressException('wordpress_connection', true);
        }

        return [CURLOPT_RESOLVE => [PublicNetwork::curlResolveEntry($host, $port, $addresses)]];
    }
}
