<?php

namespace Modules\AutoFix\Handlers;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Articles\Queries\ArticleVersionsQuery;
use Modules\Articles\Queries\CompletedFixIterationsQuery;
use Modules\Articles\Services\ArticleVersionService;
use Modules\Articles\Services\ArticleViewService;
use Modules\Articles\Support\ContentHash;
use Modules\AutoFix\Commands\FixReportCommand;
use Modules\AutoFix\Queries\FixesForVersionQuery;
use Modules\AutoFix\Support\FixPolicy;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Data\StageResult;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Support\CallUsage;
use Modules\Qa\Queries\LatestQaQuery;
use Modules\Qa\Support\QaSnapshot;

final class AutoFixHandler extends BaseStageHandler
{
    public function __construct(
        private readonly LatestQaQuery $latestQa,
        private readonly ArticleViewService $views,
        private readonly ArticleVersionsQuery $versions,
        private readonly CompletedFixIterationsQuery $fixIterations,
        private readonly ArticleVersionService $versionService,
        private readonly FixReportCommand $reports,
        private readonly FixesForVersionQuery $fixes,
    ) {}

    public function kind(): JobKind
    {
        return JobKind::AutoFixArticle;
    }

    public function prepare(Candidate $candidate, array $options): array
    {
        $article = Article::query()->whereKey($options['article_id'] ?? 0)->lockForUpdate()->first();
        if ($article === null || $article->candidate_id !== $candidate->id) {
            throw new JobInputException('Article version not found', 404);
        }
        $report = $this->latestQa->execute($article->id, completedOnly: true);
        if ($report === null || ! QaSnapshot::matches($report, $article)) {
            throw new JobInputException('Auto Fix wymaga aktualnego ukończonego QA.');
        }
        $versions = $this->versions->execute($candidate->id)->keyBy('id')->all();
        $iteration = $this->views->iterationsUsed($article, $versions, $this->fixIterations->execute(array_keys($versions))) + 1;
        if ($iteration > config('content.ai.settings.auto_fix_max_iterations')) {
            throw new JobInputException('Limit Auto Fix został osiągnięty. Wymagana ręczna weryfikacja.');
        }
        $issues = $report->issues()->get()->keyBy('id');
        $requested = $options['issue_ids'] ?? null;
        if ($requested === null) {
            $selected = $issues->filter(fn ($issue) => $issue->auto_fixable)->values();
        } else {
            if (array_diff($requested, $issues->keys()->all()) !== []) {
                throw new JobInputException('Issue IDs nie należą do QA tej wersji.', 422);
            }
            $selected = collect($requested)->map(fn ($id) => $issues[$id]);
        }
        $context = QaSnapshot::build($article);
        $context['issues'] = $selected->map(function ($issue) {
            $data = $issue->only(['id', 'type', 'severity', 'excerpt', 'reason', 'suggestion', 'section_heading', 'fact_ids', 'source_ids', 'auto_fixable']);

            return [...$data, 'auto_fixable' => FixPolicy::eligible($data)];
        })->values()->all();
        if (! collect($context['issues'])->contains('auto_fixable', true)) {
            throw new JobInputException('Brak bezpiecznych issues do Auto Fix.');
        }

        return ['fix_context' => [...$context, 'qa_id' => $report->id, 'iteration' => $iteration]];
    }

    public function created(PipelineJob $job): void
    {
        $job->update(['article_id' => $job->payload['options']['article_id']]);
        $this->reports->createPending($job->article_id, $job->id, $job->payload['fix_context']);
    }

    public function run(PipelineJob $job, JobRunContext $context): void
    {
        $fix = $this->fixes->forJob($job->id) ?? throw new JobInputException('Article fix not found', 404);
        $context->transaction(fn () => $this->reports->status($fix, 'running'));
        $context->stage('fixing_article');
        $response = $context->ai('fix', 'autofix.fix', [
            'payload' => $fix->input_snapshot,
            'max_change_ratio' => config('content.ai.settings.auto_fix_max_change_ratio'),
        ]);
        $context->stage('validating_fix');
        $result = $response['result'];
        $article = Article::query()->with('candidate')->findOrFail($job->article_id);
        if (ContentHash::of($article->only(ContentHash::FIELDS)) !== ContentHash::of($fix->input_snapshot['article'])) {
            throw new JobInputException('Wersja źródłowa zmieniła się podczas poprawki.');
        }
        $child = $result['changed']
            ? $this->versionService->prepareChild($article, [...$result['article'], 'lead_fact_ids' => $result['lead_fact_ids']],
                'auto_fix', $fix->iteration, $result['patches'])
            : null;
        $context->finish(function () use ($fix, $article, $result, $response, $child): StageResult {
            $version = $child === null ? null : $this->versionService->store($article->candidate_id, $child);
            if ($version === null) {
                $article->update(['status' => ArticleStatus::ManualReviewRequired]);
            }
            $this->reports->complete($fix, $result, CallUsage::of($response['calls']), $version?->id);

            return new StageResult('article_fix', $fix->id);
        });
    }

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void
    {
        $fix = $this->fixes->forJob($job->id);
        if ($fix !== null) {
            $this->reports->fail($fix, $final ? 'failed' : 'pending', $message);
        }
    }
}
