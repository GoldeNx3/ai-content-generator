<?php

namespace Modules\Articles\Services;

use Modules\Ai\Services\AiRunner;
use Modules\Articles\Commands\SaveSeoPreviewCommand;
use Modules\Articles\Models\Article;
use Modules\WordPress\Queries\PublicationForCandidateQuery;

final class SeoPreviewService
{
    private const TIMEOUT = 60;

    public function __construct(
        private readonly AiRunner $ai,
        private readonly PublicationForCandidateQuery $publication,
        private readonly SaveSeoPreviewCommand $savePreview,
    ) {}

    public function compute(array $article, int $candidateId, ?int $articleId, array $lineage, bool $demo): array
    {
        [$profile, $matches] = $this->publicationProfile($candidateId, $articleId, $lineage);

        return $this->ai->run('seo.preview', [
            'article' => $article,
            'publication_profile' => $profile,
            'profile_version_matches' => $matches,
        ], $demo, self::TIMEOUT)->result;
    }

    public function refresh(Article $article, array $lineage): void
    {
        $preview = $this->compute($this->fields($article), $article->candidate_id, $article->id, $lineage, $article->candidate->isDemo());
        $this->savePreview->execute($article, $preview['seo_preview'], $preview['seo_origin']);
    }

    public function fields(Article $article): array
    {
        return [
            'title' => $article->title, 'slug' => $article->slug, 'lead' => $article->lead, 'content' => $article->content,
            'meta_title' => $article->meta_title, 'meta_description' => $article->meta_description,
            'article_type' => $article->article_type->value, 'seo_data' => $article->seo_data ?? [],
            'research_snapshot' => $article->research_snapshot ?? [], 'sections' => $article->sections ?? [],
        ];
    }

    private function publicationProfile(int $candidateId, ?int $articleId, array $lineage): array
    {
        $publication = $this->publication->execute($candidateId);
        $profile = $publication?->profile ?? [];
        if ($publication === null || ! isset($profile['version_id'])) {
            return [null, false];
        }
        if ($articleId !== null && $profile['version_id'] === $articleId) {
            return [$profile, true];
        }

        return in_array($profile['version_id'], $lineage, true) ? [$profile, false] : [null, false];
    }
}
