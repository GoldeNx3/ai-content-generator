<?php

namespace Modules\Sources\Services;

use Carbon\CarbonImmutable;
use GuzzleHttp\Psr7\Uri;
use GuzzleHttp\Psr7\UriResolver;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Factory as Http;
use Illuminate\Http\Client\Response;
use Modules\Shared\Support\PublicNetwork;
use Modules\Sources\Data\FeedEntryData;
use Modules\Sources\Exceptions\FeedFetchException;
use SimplePie\SimplePie;

final class FeedReader
{
    private const SUMMARY_MAX_LENGTH = 2000;

    private const MAX_BYTES = 5 * 1024 * 1024;

    private const MAX_REDIRECTS = 3;

    private const MAX_LINK_LENGTH = 2048;

    private const USER_AGENT = 'ContentEngine/1.0 (+https://github.com/content-engine)';

    public function __construct(private readonly Http $http) {}

    public function read(string $url): array
    {
        return $this->parse($this->download($url), $url);
    }

    public function parse(string $content, string $url = ''): array
    {
        $feed = new SimplePie;
        $feed->enable_cache(false);
        $feed->set_raw_data($content);
        $feed->enable_order_by_date(false);
        if (! $feed->init() || $feed->error()) {
            throw new FeedFetchException("Invalid feed {$url}: ".(is_array($feed->error()) ? implode('; ', $feed->error()) : $feed->error()));
        }
        $entries = [];
        foreach ($feed->get_items() ?? [] as $item) {
            $link = trim((string) $item->get_permalink());
            $title = $this->clean($item->get_title());
            if ($link === '' || $title === '' || strlen($link) > self::MAX_LINK_LENGTH || PublicNetwork::hasCredentialsOrBadScheme($link)) {
                continue;
            }
            $summary = $this->clean($item->get_description() ?: $item->get_content());
            if (mb_strlen($summary) > self::SUMMARY_MAX_LENGTH) {
                $summary = rtrim(mb_substr($summary, 0, self::SUMMARY_MAX_LENGTH - 1)).'…';
            }
            $timestamp = $item->get_gmdate('U') ?: $item->get_updated_gmdate('U');
            $entries[] = new FeedEntryData(
                mb_substr($title, 0, 1000),
                $link,
                $summary !== '' ? $summary : null,
                $timestamp ? CarbonImmutable::createFromTimestampUTC((int) $timestamp) : null,
            );
        }

        return $entries;
    }

    private function download(string $url): string
    {
        for ($hop = 0; $hop <= self::MAX_REDIRECTS; $hop++) {
            $response = $this->request($url);
            if ($response->redirect()) {
                $location = (string) $response->header('Location');
                $url = $location === '' ? '' : (string) UriResolver::resolve(new Uri($url), new Uri($location));
                if ($url === '') {
                    throw new FeedFetchException('Redirect without location');
                }

                continue;
            }
            if (! $response->successful()) {
                throw new FeedFetchException("HTTP {$response->status()} for {$url}");
            }
            $body = $response->body();
            if (strlen($body) > self::MAX_BYTES) {
                throw new FeedFetchException('Feed larger than '.self::MAX_BYTES." bytes: {$url}");
            }

            return $body;
        }

        throw new FeedFetchException("Too many redirects for {$url}");
    }

    private function request(string $url): Response
    {
        $request = $this->http->timeout(config('content.ingestion.http_timeout_seconds'))
            ->withoutRedirecting()
            ->withHeaders([
                'User-Agent' => self::USER_AGENT,
                'Accept' => 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
            ])
            ->withOptions(['curl' => [CURLOPT_MAXFILESIZE => self::MAX_BYTES]]);
        if (! config('content.sources.allow_private_urls')) {
            if (PublicNetwork::hasCredentialsOrBadScheme($url)) {
                throw new FeedFetchException("Unsupported feed URL {$url}");
            }
            $parts = parse_url($url);
            $host = $parts['host'];
            $addresses = PublicNetwork::publicAddresses($host);
            if ($addresses === null || $addresses === []) {
                throw new FeedFetchException("Feed host is not a public address: {$host}");
            }
            $port = $parts['port'] ?? (strtolower($parts['scheme']) === 'https' ? 443 : 80);
            $request = $request->withOptions(['curl' => [
                CURLOPT_MAXFILESIZE => self::MAX_BYTES,
                CURLOPT_RESOLVE => [PublicNetwork::curlResolveEntry($host, $port, $addresses)],
            ]]);
        }
        try {
            return $request->get($url);
        } catch (ConnectionException $exception) {
            throw new FeedFetchException("Request failed for {$url}: {$exception->getMessage()}", previous: $exception);
        }
    }

    private function clean(?string $value): string
    {
        if ($value === null || $value === '') {
            return '';
        }
        $text = html_entity_decode(preg_replace('/<[^>]+>/', ' ', $value) ?? '', ENT_QUOTES | ENT_HTML5, 'UTF-8');

        return trim(preg_replace('/\s+/u', ' ', $text) ?? '');
    }
}
