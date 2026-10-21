<?php

namespace Modules\WordPress\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Queries\ActiveCandidateJobQuery;
use Modules\Pipeline\Services\EnqueueService;
use Modules\WordPress\Client\WordPressClientFactory;
use Modules\WordPress\Commands\FindOrCreatePublicationCommand;
use Modules\WordPress\Commands\UpdatePublicationCommand;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Data\PublicationData;
use Modules\WordPress\Data\PublishData;
use Modules\WordPress\Data\SyncData;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Models\WordPressPublication;
use Modules\WordPress\Queries\ConnectionForWorkspaceQuery;
use Modules\WordPress\Queries\PublicationForCandidateQuery;
use Modules\WordPress\Support\PublicationGate;
use Modules\WordPress\Support\Readiness;

final class PublicationService
{
    public function __construct(
        private readonly PublicationForCandidateQuery $publicationFor,
        private readonly ConnectionForWorkspaceQuery $connectionFor,
        private readonly WordPressClientFactory $clients,
        private readonly PublicationGate $gate,
        private readonly ProfileService $profiles,
        private readonly FindOrCreatePublicationCommand $findOrCreatePublication,
        private readonly UpdatePublicationCommand $updatePublication,
        private readonly ActiveCandidateJobQuery $activeJob,
        private readonly EnqueueService $enqueue,
    ) {}

    public function state(Article $article): array
    {
        $publication = $this->publicationFor->execute($article->candidate_id);
        $profile = $this->profiles->stored($article, $publication);
        $connection = $this->connectionFor->execute($article->candidate->workspace_id);
        $linked = $publication?->wordpress_post_id !== null && $connection !== null
            && $publication->wordpress_instance_id === $connection->instance_id;
        $remote = null;
        if ($linked) {
            try {
                $remote = $this->clients->make(ConnectionConfig::fromModel($connection))->getPost($publication->wordpress_post_id)['status'] ?? null;
            } catch (WordPressException $exception) {
                $remote = $exception->errorCode === 'wordpress_http_404' ? 'missing' : 'unknown';
            }
        }
        $qaOk = $this->gate->qaOk($article);
        $approved = Article::query()->where('candidate_id', $article->candidate_id)->where('status', ArticleStatus::Approved->value)->value('id');

        return [
            'publication' => $publication === null ? null : PublicationData::fromModel($publication),
            'profile' => $profile,
            'remote_status' => $remote,
            'checks' => Readiness::checks($article, $profile, $qaOk),
            'categories' => Readiness::CATEGORIES,
            'qa_ok' => $qaOk,
            'newer_approved_version_id' => $publication !== null && $approved !== null && $approved !== $publication->article_version_id ? $approved : null,
            'conflict' => $publication !== null && ! in_array($remote, ['missing', 'trash'], true) ? $publication->conflict : null,
            'wordpress_connected' => $connection !== null,
            'wordpress_admin_url' => $linked ? rtrim($connection->site_url, '/')."/wp-admin/post.php?post={$publication->wordpress_post_id}&action=edit" : null,
        ];
    }

    public function updateSettings(Article $article, array $values): array
    {
        if (isset($values['category'])) {
            $values['category_override'] = true;
        }
        DB::transaction(function () use ($article, $values): void {
            $article = $this->gate->approved($article, lock: true);
            if ($this->activeJob->execute($article->candidate_id) !== null) {
                throw new JobInputException('Poczekaj na zakończenie aktywnego zadania.');
            }
            $publication = $this->findOrCreatePublication->execute($article);
            $resolved = $this->profiles->resolve($article, [...($article->seo_preview ?? []), ...$this->profiles->overrides($article, $publication)]);
            $this->updatePublication->execute($publication, ['profile' => [...$resolved, ...$values, 'version_id' => $article->id]]);
        });

        return $this->state($article->refresh());
    }

    public function publish(Article $article, PublishData $data, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::PublishWordPress, $article->candidate_id, ['article_id' => $article->id, ...$data->options()], $key);
    }

    public function prepare(Article $article, ?string $key): PipelineJob
    {
        return $this->enqueue->enqueue(JobKind::PrepareWordPress, $article->candidate_id, ['article_id' => $article->id], $key);
    }

    public function sync(Article $article, SyncData $data, ?string $key): PipelineJob
    {
        $article = $this->gate->approved($article);
        $publication = $this->publicationFor->execute($article->candidate_id);
        if ($publication?->wordpress_post_id === null) {
            throw new JobInputException('Najpierw utwórz draft WordPress.');
        }
        $connection = $this->connectionFor->execute($article->candidate->workspace_id) ?? throw new JobInputException('wordpress_not_configured', 503);
        try {
            $remote = $this->clients->make(ConnectionConfig::fromModel($connection))->getPost($publication->wordpress_post_id);
        } catch (WordPressException $exception) {
            if ($exception->errorCode !== 'wordpress_http_404') {
                throw new JobInputException($exception->errorCode, 503);
            }
            $remote = ['status' => 'draft'];
        }
        $status = $data->status ?? ($remote['status'] === 'trash' ? 'draft' : $remote['status']);
        $scheduled = $data->scheduled_at;
        if ($status === 'future' && $scheduled === null) {
            $scheduled = isset($remote['date_gmt']) ? $remote['date_gmt'].'Z' : $publication->scheduled_at?->toIso8601String();
        }
        try {
            $publish = PublishData::validateAndCreate(['status' => $status, 'scheduled_at' => $scheduled, 'expected_wp_hash' => $data->expected_wp_hash]);
        } catch (\Illuminate\Validation\ValidationException) {
            throw new JobInputException('Nieprawidłowy termin publikacji; wybierz przyszłą datę ze strefą czasową.', 422);
        }

        return $this->enqueue->enqueue(JobKind::PublishWordPress, $article->candidate_id, ['article_id' => $article->id, ...$publish->options(), 'sync' => true], $key);
    }
}
