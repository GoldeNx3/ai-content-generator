<?php

namespace Tests\Feature\Candidates;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class TopicGroupingTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private const SCORES = ['relevance' => 80, 'freshness' => 70, 'search_potential' => 60, 'commercial_potential' => 50, 'total_score' => 68, 'category' => 'news', 'reason' => 'Ocena AI.'];

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        config(['content.topics.similarity_threshold' => 0.86]);
        $this->fakeAi([
            'embed' => fn (array $request) => self::aiOk(['vectors' => array_map(fn (string $text) => self::vectorFor($text), $request['input']['texts']), 'model' => 'text-embedding-3-small'],
                [self::llmCall('embedding', '0.000001', 'text-embedding-3-small')]),
            'classify' => fn (array $request) => self::aiOk([...self::SCORES, 'reason' => isset($request['input']['candidate']['already_covered']) ? 'Uwaga: już opisane.' : 'Ocena AI.']),
        ]);
    }

    private static function vectorFor(string $text): array
    {
        return match (true) {
            str_contains($text, 'OpenAI') => [1.0, 0.0, 0.0],
            str_contains($text, 'GPT-6') => [0.95, 0.31, 0.0],
            default => [0.0, 0.0, 1.0],
        };
    }

    private function classify(Candidate $candidate, array $body = []): void
    {
        $this->postJson("/api/candidates/{$candidate->id}/classify", $body)->assertStatus(202);
    }

    private function aiTasks(): array
    {
        return array_column($this->aiRequests, 'task');
    }

    #[Test]
    public function the_same_story_from_another_feed_joins_the_group_without_a_paid_classification(): void
    {
        $first = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);
        $this->classify($first);
        $this->aiRequests = [];
        $second = $this->makeCandidate(['title' => 'Nowy model GPT-6 od firmy'], null);

        $this->classify($second);

        $second->refresh();
        $this->assertSame($first->id, $second->topic_group_id);
        $this->assertSame(68, $second->total_score);
        $this->assertStringContainsString("#{$first->id}", $second->llm_reason);
        $this->assertSame(['embed'], $this->aiTasks());
        $this->assertNull($first->refresh()->topic_group_id);
    }

    #[Test]
    public function forcing_a_classification_keeps_the_topic_separate(): void
    {
        $first = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);
        $this->classify($first);
        $second = $this->makeCandidate(['title' => 'Nowy model GPT-6 od firmy']);
        $this->aiRequests = [];

        $this->classify($second, ['force' => true]);

        $this->assertContains('classify', $this->aiTasks());
        $this->assertNull($second->refresh()->topic_group_id);
    }

    #[Test]
    public function reclassifying_a_group_primary_classifies_it_again_and_keeps_its_group(): void
    {
        $first = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);
        $this->classify($first);
        $second = $this->makeCandidate(['title' => 'Nowy model GPT-6 od firmy']);
        $this->classify($second);
        $this->aiRequests = [];

        $this->classify($first);

        $this->assertContains('classify', $this->aiTasks());
        $this->assertNull($first->refresh()->topic_group_id);
        $this->assertSame($first->id, $second->refresh()->topic_group_id);
        $this->getJson('/api/candidates')->assertJsonPath('items.0.id', $first->id)->assertJsonPath('items.0.group_size', 2);
    }

    #[Test]
    public function a_group_primary_never_joins_another_group(): void
    {
        $other = $this->makeCandidate(['title' => 'OpenAI pokazało model']);
        $first = $this->makeCandidate(['title' => 'Kubernetes zmienia API']);
        $this->classify($first);
        $member = $this->makeCandidate(['title' => 'Kubernetes i nowe API']);
        DB::table('candidates')->where('id', $member->id)->update(['topic_group_id' => $first->id]);
        $this->classify($other);
        DB::table('candidates')->where('id', $first->id)->update(['title' => 'OpenAI wydało nowy model']);
        $this->aiRequests = [];

        $this->classify($first->refresh());

        $this->assertContains('classify', $this->aiTasks());
        $this->assertNull($first->refresh()->topic_group_id);
    }

    #[Test]
    public function a_failed_embedding_falls_back_to_a_normal_classification(): void
    {
        $this->fakeAi(['embed' => self::aiError('openai_bad_request'), 'classify' => self::aiOk(self::SCORES)]);
        $candidate = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);

        $this->classify($candidate);

        $candidate->refresh();
        $this->assertSame(68, $candidate->total_score);
        $this->assertNull(DB::table('candidates')->where('id', $candidate->id)->value('embedding'));
    }

    #[Test]
    public function different_topics_and_other_accounts_are_never_grouped(): void
    {
        $foreign = $this->makeCandidate(['title' => 'OpenAI wydało nowy model'], $this->otherWorkspace()->id);
        DB::table('candidates')->where('id', $foreign->id)->update(['embedding' => '{1,0,0}', 'total_score' => 90]);
        $other = $this->makeCandidate(['title' => 'Kubernetes zmienia API']);
        $this->classify($other);
        $mine = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);
        $this->aiRequests = [];

        $this->classify($mine);

        $this->assertNull($mine->refresh()->topic_group_id);
        $this->assertContains('classify', $this->aiTasks());
    }

    #[Test]
    public function a_topic_already_covered_by_an_article_is_flagged_for_the_classifier(): void
    {
        $article = $this->makeArticle($this->makeCandidate(['title' => 'Stary temat']), ['title' => 'OpenAI i nowy model – analiza']);
        DB::table('articles')->where('id', $article->id)->update(['embedding' => '{1,0,0}']);
        $candidate = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);

        $this->classify($candidate);

        $request = collect($this->aiRequests)->firstWhere('task', 'classify');
        $this->assertSame('OpenAI i nowy model – analiza', $request['input']['candidate']['already_covered']['title']);
        $this->assertSame('Uwaga: już opisane.', $candidate->refresh()->llm_reason);
    }

    #[Test]
    public function the_topic_list_shows_one_row_per_group_with_its_size(): void
    {
        $first = $this->makeCandidate(['title' => 'OpenAI wydało nowy model']);
        $this->classify($first);
        $second = $this->makeCandidate(['title' => 'Nowy model GPT-6 od firmy']);
        $this->classify($second);

        $this->getJson('/api/candidates')->assertJsonPath('total', 1)
            ->assertJsonPath('items.0.id', $first->id)->assertJsonPath('items.0.group_size', 2);
        $this->getJson('/api/candidates?duplicates=1')->assertJsonPath('total', 2);
        $this->getJson("/api/candidates/{$second->id}")->assertJsonPath('topic_group.primary_id', $first->id)
            ->assertJsonPath('topic_group.members.0.id', $first->id);
    }

    #[Test]
    public function research_uses_the_other_reports_of_the_same_story_as_sources(): void
    {
        $primary = $this->makeCandidate(['title' => 'OpenAI wydało nowy model', 'external_url' => 'https://a.example/openai']);
        $sibling = $this->makeCandidate(['title' => 'Nowy model GPT-6', 'external_url' => 'https://b.example/gpt6']);
        $foreign = $this->makeCandidate(['title' => 'OpenAI', 'external_url' => 'https://c.example/x'], $this->otherWorkspace()->id);
        DB::table('candidates')->where('id', $sibling->id)->update(['topic_group_id' => $primary->id]);
        $extraction = fn (string $url) => ['url' => $url, 'source_type' => 'news', 'source_score' => 70, 'fetch_status' => 'success', 'http_status' => 200,
            'error' => null, 'title' => 'T', 'publisher' => 'P', 'published_at' => null, 'extracted_content' => 'Treść', 'raw_content' => '<p>x</p>'];
        $this->fakeAi([
            'research.extract' => fn (array $r) => self::aiOk(['sources' => array_map($extraction, $r['input']['urls'])]),
            'research.discover' => self::aiOk(['queries' => [], 'sources' => []]),
            'research.analyse' => fn (array $r) => self::aiOk(['summary' => 's', 'why_it_matters' => 'w', 'suggested_angle' => 'a', 'uncertainties' => [], 'conflicts' => [],
                'facts' => [], 'source_updates' => []]),
        ]);

        $this->postJson("/api/candidates/{$primary->id}/research")->assertStatus(202);

        $urls = collect($this->aiRequests)->firstWhere('task', 'research.extract')['input']['urls'];
        $this->assertContains('https://b.example/gpt6', $urls);
        $this->assertNotContains('https://c.example/x', $urls);
        $this->assertSame('sibling', DB::table('research_sources')->where('url', 'https://b.example/gpt6')->value('origin'));
    }
}
