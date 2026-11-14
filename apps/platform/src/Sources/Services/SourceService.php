<?php

namespace Modules\Sources\Services;

use Illuminate\Support\Collection;
use Modules\Shared\Exceptions\ApiException;
use Modules\Shared\Support\PublicNetwork;
use Modules\Sources\Commands\CreateSourceCommand;
use Modules\Sources\Commands\DeleteSourceCommand;
use Modules\Sources\Commands\UpdateSourceCommand;
use Modules\Sources\Data\CreateSourceData;
use Modules\Sources\Data\SourceData;
use Modules\Sources\Data\UpdateSourceData;
use Modules\Sources\Models\Source;
use Modules\Sources\Queries\ListSourcesQuery;
use Modules\Sources\Queries\SourceCountQuery;
use Modules\Sources\Queries\SourceHasJobHistoryQuery;
use Modules\Sources\Queries\SourceUrlTakenQuery;
use Spatie\LaravelData\Optional;

final class SourceService
{
    private const MAX_SOURCES = 200;

    public function __construct(
        private readonly ListSourcesQuery $list,
        private readonly SourceUrlTakenQuery $urlTaken,
        private readonly SourceHasJobHistoryQuery $hasJobHistory,
        private readonly CreateSourceCommand $create,
        private readonly UpdateSourceCommand $update,
        private readonly DeleteSourceCommand $delete,
        private readonly SourceCountQuery $sourceCount,
    ) {}

    public function list(int $workspaceId): Collection
    {
        return $this->list->execute($workspaceId)->map(fn (Source $source) => SourceData::fromModel($source));
    }

    public function create(int $workspaceId, CreateSourceData $data): SourceData
    {
        $this->ensureSafeUrl($data->url);
        if ($this->sourceCount->execute($workspaceId) >= self::MAX_SOURCES) {
            throw new ApiException('source_limit_reached', 422);
        }
        if ($this->urlTaken->execute($data->url, $workspaceId)) {
            throw ApiException::plain('Source with this URL already exists', 409);
        }

        return SourceData::fromModel($this->create->execute($workspaceId, trim($data->name), $data->url, $data->type, $data->active));
    }

    public function update(Source $source, UpdateSourceData $data): SourceData
    {
        $attributes = array_filter(
            ['name' => $data->name instanceof Optional ? $data->name : trim($data->name), 'url' => $data->url, 'active' => $data->active],
            fn ($value) => ! $value instanceof Optional,
        );
        if (isset($attributes['url'])) {
            $this->ensureSafeUrl($attributes['url']);
        }
        if (isset($attributes['url']) && $this->urlTaken->execute($attributes['url'], $source->workspace_id, $source->id)) {
            throw ApiException::plain('Source with this URL already exists', 409);
        }

        return SourceData::fromModel($this->update->execute($source, $attributes));
    }

    public function delete(Source $source): void
    {
        if ($this->hasJobHistory->execute($source->id)) {
            throw ApiException::plain('Źródło ma historię zadań i nie może zostać usunięte.', 409);
        }
        $this->delete->execute($source);
    }

    private function ensureSafeUrl(string $url): void
    {
        if (PublicNetwork::hasCredentialsOrBadScheme($url)) {
            throw new ApiException('source_url_invalid', 422);
        }
        if (! config('content.sources.allow_private_urls') && PublicNetwork::publicAddresses((string) parse_url($url, PHP_URL_HOST)) === null) {
            throw new ApiException('source_private_url', 422);
        }
    }
}
