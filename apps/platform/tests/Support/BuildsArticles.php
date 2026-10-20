<?php

namespace Tests\Support;

use Modules\Articles\Models\Article;
use Modules\Articles\Support\ContentHash;
use Modules\Candidates\Models\Candidate;
use Modules\Research\Models\Research;
use Modules\Research\Models\ResearchFact;
use Modules\Research\Models\ResearchSource;

trait BuildsArticles
{
    protected function completedResearch(Candidate $candidate): Research
    {
        $research = Research::query()->create(['candidate_id' => $candidate->id, 'status' => 'completed', 'summary' => 'Sum']);
        $source = ResearchSource::query()->create([
            'research_id' => $research->id, 'url' => $candidate->external_url, 'origin' => 'original',
            'fetch_status' => 'success', 'extracted_content' => 'Treść', 'source_type' => 'official', 'source_score' => 100,
        ]);
        $fact = ResearchFact::query()->create(['research_id' => $research->id, 'claim' => 'Fakt', 'importance' => 'critical', 'confidence' => 90]);
        $fact->sources()->attach($source->id);

        return $research;
    }

    protected static function writtenArticle(array $overrides = []): array
    {
        return [
            'title' => 'Tytuł', 'slug' => 'tytul', 'lead' => 'Lead.', 'content' => "## Sekcja\n\nTreść.\n",
            'generated_content' => "## Sekcja\n\nTreść.\n", 'seo_data' => ['excerpt' => 'E'], 'meta_title' => 'Meta',
            'meta_description' => 'Opis', 'article_type' => 'news', 'angle' => 'Kąt', 'brief' => ['article_format' => 'news'],
            'sections' => [['heading' => 'Sekcja', 'content' => 'Treść.', 'used_fact_ids' => [1], 'source_ids' => [1]]],
            'lead_fact_ids' => [], 'generation_options' => ['length' => 'auto'],
            'research_snapshot' => ['facts' => [['id' => 1, 'claim' => 'Fakt']], 'sources' => [['id' => 1, 'url' => 'https://x']]],
            'validation_warnings' => [], 'word_count' => 3, 'sections_count' => 1, 'facts_used_count' => 1,
            'facts_available_count' => 1, 'source_count' => 1, 'seo_preview' => ['excerpt' => 'E', 'tags' => []], 'seo_origin' => 'article',
            ...$overrides,
        ];
    }

    protected function makeArticle(Candidate $candidate, array $overrides = []): Article
    {
        $data = self::writtenArticle($overrides);
        $data['research_snapshot'] = [...$data['research_snapshot'], 'candidate_id' => $candidate->id];

        return Article::query()->create([...$data, 'candidate_id' => $candidate->id, 'version' => $overrides['version'] ?? 1,
            'content_hash' => ContentHash::of($data)]);
    }
}
