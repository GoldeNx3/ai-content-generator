<?php

namespace Modules\Sources\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Modules\Candidates\Commands\InsertCandidatesCommand;
use Modules\Candidates\Queries\ExistingCandidateUrlsQuery;
use Modules\Sources\Commands\MarkSourceFetchedCommand;
use Modules\Sources\Data\FeedEntryData;
use Modules\Sources\Data\FetchResultData;
use Modules\Sources\Exceptions\FeedFetchException;
use Modules\Sources\Models\Source;
use Modules\Sources\Queries\ListSourcesQuery;
use Throwable;

final class IngestionService
{
    public function __construct(
        private readonly FeedReader $reader,
        private readonly ListSourcesQuery $sources,
        private readonly ExistingCandidateUrlsQuery $existingUrls,
        private readonly InsertCandidatesCommand $insertCandidates,
        private readonly MarkSourceFetchedCommand $markFetched,
    ) {}

    public function fetchAllActive(?int $workspaceId): FetchResultData
    {
        $total = new FetchResultData;
        foreach ($this->sources->execute($workspaceId, activeOnly: true) as $source) {
            $total = $total->add($this->fetchSource($source));
        }

        return $total;
    }

    public function fetchSource(Source $source): FetchResultData
    {
        try {
            $entries = $this->reader->read($source->url);
        } catch (FeedFetchException $exception) {
            Log::warning('Fetching source failed', ['source_id' => $source->id, 'error' => $exception->getMessage()]);

            return new FetchResultData(sources_processed: 1, errors: 1);
        }
        $fresh = $this->dropOld($entries);
        try {
            $new = DB::transaction(function () use ($source, $fresh): int {
                $inserted = $this->saveNew($source, $fresh);
                $this->markFetched->execute($source);

                return $inserted;
            });
        } catch (Throwable $exception) {
            Log::error('Saving candidates failed', ['source_id' => $source->id, 'error' => $exception->getMessage()]);

            return new FetchResultData(sources_processed: 1, items_found: count($entries), skipped_old: count($entries) - count($fresh), errors: 1);
        }

        return new FetchResultData(
            sources_processed: 1,
            items_found: count($entries),
            new_candidates: $new,
            duplicates: count($fresh) - $new,
            skipped_old: count($entries) - count($fresh),
        );
    }

    private function dropOld(array $entries): array
    {
        $days = config('content.ingestion.fetch_max_age_days');
        if ($days <= 0) {
            return $entries;
        }
        $cutoff = CarbonImmutable::now()->subDays($days);

        return array_values(array_filter(
            $entries,
            fn (FeedEntryData $entry) => $entry->published_at === null || $entry->published_at->greaterThanOrEqualTo($cutoff),
        ));
    }

    private function saveNew(Source $source, array $entries): int
    {
        $unique = [];
        foreach ($entries as $entry) {
            $unique[$entry->url] ??= $entry;
        }
        $existing = array_flip($this->existingUrls->execute($source->workspace_id, array_keys($unique)));
        $rows = [];
        foreach ($unique as $url => $entry) {
            if (! isset($existing[$url])) {
                $rows[] = [
                    'workspace_id' => $source->workspace_id,
                    'source_id' => $source->id,
                    'external_url' => $url,
                    'title' => $entry->title,
                    'summary' => $entry->summary,
                    'original_published_at' => $entry->published_at,
                ];
            }
        }

        return $this->insertCandidates->execute($rows);
    }
}
