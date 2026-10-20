<?php

namespace Modules\Articles\Services;

use Modules\Articles\Data\ArticleUpdateData;
use Modules\Articles\Data\GenerateArticleData;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\EnqueueService;

final class ArticleService
{
    public function __construct(
        private readonly EnqueueService $enqueue,
        private readonly ArticleVersionService $versions,
        private readonly ApprovalService $approval,
    ) {}

    public function generate(Candidate $candidate, GenerateArticleData $data, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::Write, $candidate->id, $data->options(), $key);
    }

    public function regenerate(Article $article, array $overrides, ?string $key): PipelineJob
    {
        $options = [...GenerateArticleData::from($article->generation_options ?? [])->options(), ...$overrides];
        $options = GenerateArticleData::validateAndCreate($options)->options();

        return $this->enqueue->enqueue(JobKind::Write, $article->candidate_id, [...$options, 'parent_version_id' => $article->id], $key);
    }

    public function update(Article $article, ArticleUpdateData $data): Article
    {
        $changes = $data->changes();
        $differs = array_filter($changes, fn ($value, $field) => $article->{$field} !== $value, ARRAY_FILTER_USE_BOTH);
        if ($differs === []) {
            return $article;
        }

        return $this->versions->createChild($article, $changes, 'manual_edit');
    }

    public function setStatus(Article $article, ArticleStatus $status): Article
    {
        return match ($status) {
            ArticleStatus::Approved => $this->approval->approve($article),
            ArticleStatus::Rejected => $this->approval->reject($article, null),
            default => throw new JobInputException('Użyj QA i zatwierdzenia konkretnej wersji; ręczna zmiana tego statusu jest niedozwolona.'),
        };
    }
}
