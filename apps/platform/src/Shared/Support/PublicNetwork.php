<?php

namespace Modules\Shared\Support;

final class PublicNetwork
{
    private const BLOCKED_RANGES = [
        '0.0.0.0/8', '100.64.0.0/10', '192.0.0.0/24', '192.0.2.0/24', '198.18.0.0/15', '198.51.100.0/24',
        '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4', '64:ff9b::/96', '64:ff9b:1::/48', '100::/64', '2001:db8::/32',
        'fc00::/7', 'fe80::/10', 'ff00::/8', '::ffff:0:0:0/96', '2002::/16', '2001::/32', 'fec0::/10',
    ];

    private static $resolver = null;

    public static function resolveUsing(?callable $resolver): void
    {
        self::$resolver = $resolver;
    }

    public static function isPublicIp(string $ip): bool
    {
        $packed = @inet_pton($ip);
        if ($packed === false) {
            return false;
        }
        if (strlen($packed) === 16 && str_starts_with($packed, str_repeat("\0", 10)."\xff\xff")) {
            return self::isPublicIp((string) inet_ntop(substr($packed, 12)));
        }
        if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) {
            return false;
        }
        foreach (self::BLOCKED_RANGES as $range) {
            if (self::inRange($packed, $range)) {
                return false;
            }
        }

        return true;
    }

    public static function resolve(string $host): array
    {
        $host = trim($host, '[]');
        if (filter_var($host, FILTER_VALIDATE_IP)) {
            return [$host];
        }
        if (self::$resolver !== null) {
            return (self::$resolver)($host);
        }
        $records = @dns_get_record($host, DNS_A | DNS_AAAA) ?: [];
        $addresses = array_filter(array_map(fn ($record) => $record['ip'] ?? $record['ipv6'] ?? null, $records));
        $addresses = [...$addresses, ...(@gethostbynamel($host) ?: [])];

        return array_values(array_unique($addresses));
    }

    public static function publicAddresses(string $host): ?array
    {
        $addresses = self::resolve($host);
        foreach ($addresses as $address) {
            if (! self::isPublicIp($address)) {
                return null;
            }
        }

        return $addresses;
    }

    public static function curlResolveEntry(string $host, int $port, array $addresses): string
    {
        $formatted = array_map(fn (string $ip) => str_contains($ip, ':') ? "[{$ip}]" : $ip, $addresses);

        return trim($host, '[]').":{$port}:".implode(',', $formatted);
    }

    public static function hasCredentialsOrBadScheme(string $url): bool
    {
        $parts = parse_url($url);

        return $parts === false || ! in_array(strtolower($parts['scheme'] ?? ''), ['http', 'https'], true)
            || isset($parts['user']) || isset($parts['pass']) || ($parts['host'] ?? '') === '';
    }

    private static function inRange(string $packed, string $range): bool
    {
        [$network, $bits] = explode('/', $range);
        $networkPacked = inet_pton($network);
        if (strlen($networkPacked) !== strlen($packed)) {
            return false;
        }
        $bytes = intdiv((int) $bits, 8);
        $remainder = (int) $bits % 8;
        if (substr($packed, 0, $bytes) !== substr($networkPacked, 0, $bytes)) {
            return false;
        }
        if ($remainder === 0) {
            return true;
        }
        $mask = (0xFF << (8 - $remainder)) & 0xFF;

        return (ord($packed[$bytes]) & $mask) === (ord($networkPacked[$bytes]) & $mask);
    }
}
