<?php

namespace Modules\Demo\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Commands\InsertCandidatesCommand;
use Modules\Candidates\Models\Candidate;
use Modules\Demo\Commands\DeleteDemoDataCommand;
use Modules\Demo\Data\DemoResetData;
use Modules\Demo\Queries\DemoCandidateIdsQuery;
use Modules\Demo\Queries\DemoHasActiveJobsQuery;
use Modules\Demo\Queries\DemoSourceQuery;
use Modules\Shared\Exceptions\ApiException;
use Modules\Sources\Commands\CreateSourceCommand;

final class DemoSeedService
{
    public const CASES = [
        'discovered' => ['Zacznij tutaj — cały interaktywny flow', 'Kliknij ocenę, Research, generowanie, QA, Auto Fix i Approval. Writer celowo dodaje niepoparte 47%; Auto Fix usuwa zdanie, a nowe QA przechodzi. Wszystkie akcje demo są bezpłatne.'],
        'second-run' => ['Drugi przebieg — porównanie wersji', 'Ten sam flow na osobnym temacie: regeneracja, ręczna edycja i historia wersji bez kosztów AI.'],
        'ignored' => ['Temat pominięty', 'Decyzja redakcyjna ignored nie usuwa historii; możesz przywrócić temat do oczekujących.'],
    ];

    public function __construct(
        private readonly DemoSourceQuery $demoSource,
        private readonly CreateSourceCommand $createSource,
        private readonly InsertCandidatesCommand $insertCandidates,
        private readonly DemoCandidateIdsQuery $demoCandidates,
        private readonly DemoHasActiveJobsQuery $activeJobs,
        private readonly DeleteDemoDataCommand $deleteDemo,
    ) {}

    public function reset(int $workspaceId): DemoResetData
    {
        return DB::transaction(function () use ($workspaceId): DemoResetData {
            $ids = $this->demoCandidates->execute($workspaceId);
            if ($this->activeJobs->execute($workspaceId, $ids)) {
                throw new ApiException('demo_jobs_active', 409);
            }
            $removed = $this->deleteDemo->execute($workspaceId, $ids, self::sourceUrl());

            return new DemoResetData($removed, $this->seed($workspaceId)['created']);
        });
    }

    public static function sourceUrl(): string
    {
        return Candidate::DEMO_PREFIX.'feed.xml';
    }

    public function seed(int $workspaceId): array
    {
        return DB::transaction(function () use ($workspaceId): array {
            $url = self::sourceUrl();
            $source = $this->demoSource->execute($workspaceId, $url)
                ?? $this->createSource->execute($workspaceId, '[DEMO] Scenariusze pipeline — 0 kosztów AI', $url, 'rss', false);
            $rows = [];
            $index = 0;
            foreach (self::CASES as $slug => [$title, $summary]) {
                $index++;
                $rows[] = [
                    'workspace_id' => $workspaceId, 'source_id' => $source->id,
                    'external_url' => Candidate::DEMO_PREFIX.'cases/'.$slug,
                    'title' => sprintf('[DEMO %02d] %s', $index, $title), 'summary' => $summary,
                    'original_published_at' => CarbonImmutable::now(),
                    'status' => $slug === 'ignored' ? 'ignored' : 'pending',
                ];
            }
            $created = $this->insertCandidates->execute($rows);

            return ['created' => $created, 'source_id' => $source->id];
        });
    }
}
