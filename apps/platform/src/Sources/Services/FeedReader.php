<?php

namespace Modules\Sources\Services;

use Carbon\CarbonImmutable;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Factory as Http;
use Modules\Sources\Data\FeedEntryData;
use Modules\Sources\Exceptions\FeedFetchException;
use SimplePie\SimplePie;

final class FeedReader
{
    private const SUMMARY_MAX_LENGTH = 2000;

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
            if ($link === '' || $title === '') {
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
        try {
            $response = $this->http->timeout(config('content.ingestion.http_timeout_seconds'))
                ->withHeaders([
                    'User-Agent' => self::USER_AGENT,
                    'Accept' => 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
                ])
                ->get($url);
        } catch (ConnectionException $exception) {
            throw new FeedFetchException("Request failed for {$url}: {$exception->getMessage()}", previous: $exception);
        }
        if (! $response->successful()) {
            throw new FeedFetchException("HTTP {$response->status()} for {$url}");
        }

        return $response->body();
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
