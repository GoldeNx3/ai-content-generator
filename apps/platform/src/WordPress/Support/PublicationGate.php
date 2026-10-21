<?php

namespace Modules\WordPress\Support;

use Modules\Articles\Enums\ArticleStatus;
use Modules\Articles\Models\Article;
use Modules\Articles\Services\ApprovalService;
use Modules\Articles\Support\ContentHash;
use Modules\Pipeline\Exceptions\JobInputException;
use Modules\Pipeline\Queries\LockCandidateQuery;

final class PublicationGate
{
    public function __construct(private readonly ApprovalService $approval, private readonly LockCandidateQuery $lockCandidate) {}

    public function approved(Article $article, bool $lock = false): Article
    {
        if ($lock) {
            $this->lockCandidate->execute($article->candidate_id);
            $article = Article::query()->whereKey($article->id)->lockForUpdate()->firstOrFail();
        }
        if ($article->status !== ArticleStatus::Approved) {
            throw new JobInputException('WordPress wymaga zatwierdzonej wersji.');
        }
        if (! $this->approval->qaPasses($article)) {
            throw new JobInputException('Publikacja wymaga aktualnego, zaliczonego QA.');
        }
        if ($article->content_hash !== ContentHash::of($article->only(ContentHash::FIELDS))) {
            throw new JobInputException('Zmieniona treść wymaga nowego QA i approval.');
        }

        return $article;
    }

    public function qaOk(Article $article): bool
    {
        try {
            $this->approved($article);

            return true;
        } catch (JobInputException) {
            return false;
        }
    }
}
