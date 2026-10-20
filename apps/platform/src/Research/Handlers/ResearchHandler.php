<?php

namespace Modules\Research\Handlers;

use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\Research\Commands\FailResearchCommand;
use Modules\Research\Commands\SaveResearchAnalysisCommand;
use Modules\Research\Commands\SaveResearchSourcesCommand;
use Modules\Research\Commands\StartResearchCommand;
use Modules\Research\Enums\FetchStatus;
use Modules\Research\Enums\SourceOrigin;
use Modules\Research\Models\Research;
use Modules\Research\Models\ResearchSource;
use Modules\Research\Queries\ResearchForCandidateQuery;
use Modules\Research\Queries\ResearchSourcesQuery;

final class ResearchHandler extends BaseStageHandler
{
    public function __construct(
        private readonly ResearchForCandidateQuery $researchFor,
        private readonly ResearchSourcesQuery $sources,
        private readonly StartResearchCommand $start,
        private readonly SaveResearchSourcesCommand $saveSources,
        private readonly SaveResearchAnalysisCommand $saveAnalysis,
        private readonly FailResearchCommand $failResearch,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::Research;
    }

    public function prepare(Candidate $candidate, array $options): array
    {
        if (! ($options['discover'] ?? true) && $this->researchFor->execute($candidate->id, false) === null) {
            throw new JobInputException('Research not found - start a research first', 404);
        }

        return [];
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $discover = (bool) ($job->payload['options']['discover'] ?? true);
        $research = $this->begin($job, $context, $discover);
        $original = $job->payload['original_url'];

        $context->stage('fetching_original');
        $this->fetchMissing($context, $research, $original);

        $context->stage('discovering_sources');
        $discovery = null;
        if ($discover) {
            $discovery = $this->discover($job, $context, $research, $original);
        }

        $context->stage('analysing');
        $sources = $this->sources->execute($research->id);
        $analysis = $context->ai('analyse', 'research.analyse', [
            'candidate' => $job->payload['candidate_input'],
            'original_url' => $original,
            'sources' => $sources->map(fn (ResearchSource $source) => [
                'id' => $source->id, 'url' => $source->url, 'origin' => $source->origin->value, 'title' => $source->title,
                'publisher' => $source->publisher, 'published_at' => $source->published_at?->toIso8601String(),
                'extracted_content' => $source->extracted_content, 'fetch_status' => $source->fetch_status->value,
            ])->all(),
        ]);
        $calls = [...($discovery['calls'] ?? []), ...$analysis['calls']];
        $context->finish(function () use ($research, $analysis, $calls): StageResult {
            $this->saveAnalysis->execute($research, $analysis['result'], CallUsage::of($calls));

            return new StageResult('research', $research->id);
        });
    }

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void
    {
        if ($final) {
            $this->failResearch->execute($job->id, $message);
        }
    }

    private function begin(PipelineJob $job, JobRunContext $context, bool $discover): Research
    {
        $researchId = $context->checkpointValue('research_id');
        if ($researchId !== null) {
            return $context->transaction(fn () => $this->start->resume($researchId));
        }
        $research = $context->transaction(fn () => $this->start->execute($job->candidate_id, $job->id, $discover));
        $context->checkpoint('research_id', $research->id);

        return $research;
    }

    private function fetchMissing(JobRunContext $context, Research $research, string $original): void
    {
        $sources = $this->sources->execute($research->id);
        if (! $sources->contains(fn (ResearchSource $source) => $source->origin === SourceOrigin::Original)) {
            $sources->push($this->saveSources->create($research->id, $original, SourceOrigin::Original));
        }
        $pending = $sources->filter(fn (ResearchSource $source) => $source->fetch_status !== FetchStatus::Success)->values();
        if ($pending->isEmpty()) {
            return;
        }
        $extracted = $context->ai('extract:'.$context->job->attempt_count, 'research.extract', [
            'original_url' => $original,
            'urls' => $pending->pluck('url')->all(),
        ]);
        $context->transaction(function () use ($pending, $extracted): void {
            foreach ($pending as $index => $source) {
                $this->saveSources->applyExtraction($source, $extracted['result']['sources'][$index]);
            }
        });
    }

    private function discover(PipelineJob $job, JobRunContext $context, Research $research, string $original): array
    {
        $sources = $this->sources->execute($research->id, withRawContent: true);
        $originalSource = $sources->first(fn (ResearchSource $source) => $source->origin === SourceOrigin::Original);
        $discovery = $context->ai('discover', 'research.discover', [
            'candidate' => $job->payload['candidate_input'],
            'original_url' => $original,
            'original_raw_content' => $originalSource?->fetch_status === FetchStatus::Success ? $originalSource->raw_content : null,
            'known_urls' => $sources->pluck('url')->all(),
        ]);
        if ($context->checkpointValue('discovery_done') === null) {
            $context->transaction(function () use ($research, $discovery): void {
                $research->update(['search_queries' => $discovery['result']['queries']]);
                foreach ($discovery['result']['sources'] as $found) {
                    $source = $this->saveSources->create($research->id, $found['url'], SourceOrigin::Search, $found['title'] ?? null);
                    $this->saveSources->applyExtraction($source, $found);
                }
            });
            $context->checkpoint('discovery_done', true);
        }

        return $discovery;
    }
}
