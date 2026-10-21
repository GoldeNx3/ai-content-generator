<?php

namespace Modules\WordPress\Handlers;

use Modules\Articles\Models\Article;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Contracts\BaseStageHandler;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunContext;
use Modules\WordPress\Client\WordPressClientFactory;
use Modules\WordPress\Commands\PublicationCommand;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Models\WordPressPublication;
use Modules\WordPress\Queries\ConnectionForWorkspaceQuery;
use Modules\WordPress\Queries\PublicationForCandidateQuery;
use Modules\WordPress\Services\PublisherService;
use Modules\WordPress\Support\PublicationGate;

abstract class WordPressStage extends BaseStageHandler
{
    public function __construct(
        protected readonly PublicationGate $gate,
        protected readonly ConnectionForWorkspaceQuery $connectionFor,
        protected readonly PublicationForCandidateQuery $publicationFor,
        protected readonly PublicationCommand $publications,
        protected readonly WordPressClientFactory $clients,
        protected readonly PublisherService $publisher,
    ) {}

    public function prepare(Candidate $candidate, array $options): array
    {
        if ($this->connectionFor->execute($candidate->workspace_id) === null) {
            throw new JobInputException('wordpress_not_configured', 503);
        }
        $article = Article::query()->whereKey($options['article_id'] ?? 0)->where('candidate_id', $candidate->id)->first()
            ?? throw new JobInputException('Article version not found', 404);
        $this->gate->approved($article);
        if (($options['sync'] ?? false) && $this->publicationFor->execute($candidate->id)?->wordpress_post_id === null) {
            throw new JobInputException('Najpierw utwórz draft WordPress.');
        }

        return [];
    }

    public function created(PipelineJob $job): void
    {
        $article = Article::query()->findOrFail($job->payload['options']['article_id']);
        $job->update(['article_id' => $article->id]);
        $publication = $this->publications->forArticle($article);
        $this->publications->update($publication, ['job_id' => $job->id, 'status' => 'queued', 'error_code' => null, 'conflict' => null]);
    }

    public function failed(PipelineJob $job, bool $final, string $message, ?array $details): void
    {
        $publication = WordPressPublication::query()->where('job_id', $job->id)->first();
        if ($publication === null) {
            return;
        }
        $code = $job->error_code;
        $this->publications->update($publication, [
            'status' => $final ? 'failed' : 'queued',
            'error_code' => $code,
            ...($code === 'wordpress_conflict' && $details !== null ? ['conflict' => $details] : []),
        ]);
    }

    protected function context(PipelineJob $job): array
    {
        $article = Article::query()->with('candidate')->findOrFail($job->article_id);
        $connection = $this->connectionFor->execute($article->candidate->workspace_id)
            ?? throw new \Modules\WordPress\Exceptions\WordPressException('wordpress_not_configured');

        return [$article, $connection, $this->clients->make(ConnectionConfig::fromModel($connection)), $this->publications->forArticle($article)];
    }

    protected function profile(JobRunContext $context, Article $article, WordPressPublication $publication, bool $force): array
    {
        $this->gate->approved($article);

        return $this->publisher->profile($context, $article, $publication, $force);
    }
}
