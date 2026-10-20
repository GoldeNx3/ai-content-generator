<?php

namespace Modules\Qa\Support;

use Modules\Articles\Models\Article;
use Modules\Articles\Support\CanonicalJson;
use Modules\Pipeline\Exceptions\JobInputException;

final class QaSnapshot
{
    private const FIELDS = ['title', 'slug', 'lead', 'content', 'meta_title', 'meta_description', 'lead_fact_ids', 'sections'];

    public static function build(Article $article, bool $includeSeo = true): array
    {
        $snapshot = $article->research_snapshot ?? [];
        if (empty($snapshot['facts']) || empty($snapshot['sources'])) {
            throw new JobInputException('Ta wersja artykułu nie ma kompletnego snapshotu researchu.');
        }
        if (($snapshot['candidate_id'] ?? $article->candidate_id) !== $article->candidate_id) {
            throw new JobInputException('Snapshot researchu należy do innego tematu.');
        }
        if ($article->research_id !== null && ($snapshot['research_id'] ?? $article->research_id) !== $article->research_id) {
            throw new JobInputException('Snapshot researchu ma nieprawidłowe powiązanie z artykułem.');
        }
        $fields = $includeSeo && ! empty($article->seo_data) ? [...self::FIELDS, 'seo_data'] : self::FIELDS;
        $values = [];
        foreach ($fields as $field) {
            $values[$field] = $article->{$field};
        }

        return [
            'article_id' => $article->id,
            'article_version' => $article->version,
            'candidate_id' => $article->candidate_id,
            'research_id' => $article->research_id,
            'article' => $values,
            'brief' => $article->brief,
            'research' => $snapshot,
        ];
    }

    public static function hash(array $snapshot): string
    {
        return hash('sha256', CanonicalJson::encode($snapshot));
    }

    public static function matches(?object $report, Article $article): bool
    {
        if ($report === null) {
            return false;
        }
        try {
            $includeSeo = array_key_exists('seo_data', $report->input_snapshot['article'] ?? []);

            return hash_equals($report->input_hash, self::hash(self::build($article, $includeSeo)));
        } catch (JobInputException) {
            return false;
        }
    }
}
