<?php

namespace Modules\Articles\Services;

use Illuminate\Support\Facades\DB;
use Modules\Ai\Services\AiRunner;
use Modules\Articles\Commands\CreateArticleVersionCommand;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Articles\Support\Lineage;
use Modules\Articles\Queries\ArticleVersionsQuery;
use Modules\Articles\Queries\CompletedFixIterationsQuery;
use Modules\Articles\Queries\NextVersionQuery;
use Modules\Pipeline\Queries\LockCandidateQuery;

final class ArticleVersionService
{
    private const EXCLUDED = ['id', 'created_at', 'updated_at', 'generation_job_id', 'approved_at', 'approved_by', 'rejection_reason', 'version', 'is_current', 'content_hash'];

    private const TIMEOUT = 60;

    public function __construct(
        private readonly AiRunner $ai,
        private readonly SeoPreviewService $seo,
        private readonly ArticleViewService $views,
        private readonly ArticleVersionsQuery $versions,
        private readonly CompletedFixIterationsQuery $fixIterations,
        private readonly NextVersionQuery $nextVersion,
        private readonly LockCandidateQuery $lockCandidate,
        private readonly CreateArticleVersionCommand $createVersion,
    ) {}

    public function prepareChild(Article $parent, array $changes, string $createdBy, ?int $iteration = null, array $patches = []): array
    {
        $data = array_diff_key($parent->getAttributes(), array_flip(self::EXCLUDED));
        foreach (['seo_data', 'seo_preview', 'brief', 'sections', 'lead_fact_ids', 'generation_options', 'research_snapshot', 'validation_warnings', 'refresh_of'] as $json) {
            $data[$json] = $parent->{$json} ?? [];
        }
        if (empty($parent->seo_data) && $parent->seo_origin === 'publication_profile') {
            $data['seo_data'] = [...$parent->seo_preview, 'canonical_url' => null];
        }
        $data = [...$data, ...$changes];
        $versions = $this->versions->execute($parent->candidate_id)->keyBy('id')->all();
        $iteration ??= $this->views->iterationsUsed($parent, $versions, $this->fixIterations->execute(array_keys($versions)));
        $demo = $parent->candidate->isDemo();
        $rebuilt = $this->ai->run('article.rebuild', [
            'content' => $data['content'], 'lead' => $data['lead'], 'sections' => $data['sections'],
            'lead_fact_ids' => $data['lead_fact_ids'], 'research_snapshot' => $data['research_snapshot'], 'patches' => $patches,
        ], $demo, self::TIMEOUT)->result;
        $data = [...$data, ...$rebuilt,
            'status' => ArticleStatus::Draft, 'qa_passed' => false, 'parent_version_id' => $parent->id,
            'created_by' => $createdBy, 'creation_reason' => $createdBy === 'auto_fix' ? 'QA auto fix' : 'Manual edit',
            'auto_fix_iteration' => $iteration, 'is_edited' => $createdBy === 'manual_edit',
            'llm_model' => null, 'brief_llm_model' => null, 'estimated_cost_usd' => 0, 'brief_cost_usd' => 0, 'writer_cost_usd' => 0,
            'llm_input_tokens' => 0, 'llm_output_tokens' => 0, 'brief_input_tokens' => 0, 'brief_output_tokens' => 0,
            'writer_input_tokens' => 0, 'writer_output_tokens' => 0,
        ];
        if ($createdBy === 'auto_fix') {
            $data['generated_content'] = $data['content'];
        }
        $data['article_type'] = $parent->article_type->value;
        $lineage = [$parent->id, ...Lineage::walk($versions, $parent->id)];
        $preview = $this->seo->compute($data, $parent->candidate_id, null, $lineage, $demo);

        return [...$data, 'seo_preview' => $preview['seo_preview'], 'seo_origin' => $preview['seo_origin']];
    }

    public function store(int $candidateId, array $data): Article
    {
        $this->lockCandidate->execute($candidateId);

        return $this->createVersion->execute($candidateId, $this->nextVersion->execute($candidateId), $data);
    }

    public function createChild(Article $parent, array $changes, string $createdBy): Article
    {
        $data = $this->prepareChild($parent, $changes, $createdBy);

        return DB::transaction(fn () => $this->store($parent->candidate_id, $data));
    }
}
