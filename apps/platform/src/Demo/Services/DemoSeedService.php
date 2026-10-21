<?php

namespace Modules\Demo\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Commands\InsertCandidatesCommand;
use Modules\Candidates\Models\Candidate;
use Modules\Demo\Queries\DemoSourceQuery;
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
    ) {}

    public function seed(int $workspaceId): array
    {
        return DB::transaction(function () use ($workspaceId): array {
            $url = Candidate::DEMO_PREFIX.'feed.xml';
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
