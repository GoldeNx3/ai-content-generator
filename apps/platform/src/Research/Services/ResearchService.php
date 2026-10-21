<?php

namespace Modules\Research\Services;

use Illuminate\Support\Facades\DB;
use Modules\Ai\Services\AiRunner;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobConflictException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\ActiveCandidateJobQuery;
use Modules\Pipeline\Queries\LockCandidateQuery;
use Modules\Pipeline\Services\EnqueueService;
use Modules\Research\Commands\ApplySourceExtractionCommand;
use Modules\Research\Commands\CreateResearchSourceCommand;
use Modules\Research\Commands\FindOrCreateResearchCommand;
use Modules\Research\Data\ResearchData;
use Modules\Research\Data\ResearchSourceData;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Enums\SourceOrigin;
use Modules\Research\Queries\ResearchForCandidateQuery;
use Modules\Shared\Exceptions\ApiException;
use Modules\Shared\Support\UrlNormalizer;

final class ResearchService
{
    private const MANUAL_EXTRACT_TIMEOUT = 60;

    public function __construct(
        private readonly ResearchForCandidateQuery $researchFor,
        private readonly EnqueueService $enqueue,
        private readonly LockCandidateQuery $lockCandidate,
        private readonly ActiveCandidateJobQuery $activeJob,
        private readonly CreateResearchSourceCommand $createSource,
        private readonly ApplySourceExtractionCommand $applyExtraction,
        private readonly FindOrCreateResearchCommand $findOrCreateResearch,
        private readonly AiRunner $ai,
    ) {}

    public function show(Candidate $candidate): ResearchData
    {
        $research = $this->researchFor->execute($candidate->id) ?? throw ApiException::plain('Research not found', 404);

        return ResearchData::fromModel($research);
    }

    public function start(Candidate $candidate, bool $discover, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::Research, $candidate->id, ['discover' => $discover], $key);
    }

    public function addManualSource(Candidate $candidate, string $url): ResearchSourceData
    {
        $source = DB::transaction(function () use ($candidate, $url) {
            $this->lockCandidate->execute($candidate->id);
            if ($active = $this->activeJob->execute($candidate->id)) {
                throw new JobConflictException('candidate_busy', $active->id);
            }
            $research = $this->findOrCreateResearch->execute($candidate->id);
            if ($research->status === ResearchStatus::Running) {
                throw ApiException::plain('Research is running - add sources after it finishes', 409);
            }
            $normalized = UrlNormalizer::normalize($url);
            if ($research->sources()->get()->contains(fn ($source) => UrlNormalizer::normalize($source->url) === $normalized)) {
                throw ApiException::plain('This URL is already a source of this research', 409);
            }

            return $this->createSource->execute($research->id, $url, SourceOrigin::Manual);
        });
        $extracted = $this->ai->run('research.extract', ['original_url' => $candidate->external_url, 'urls' => [$url]],
            $candidate->isDemo(), self::MANUAL_EXTRACT_TIMEOUT);
        $this->applyExtraction->execute($source, $extracted->result['sources'][0]);

        return ResearchSourceData::fromModel($source->refresh());
    }
}
