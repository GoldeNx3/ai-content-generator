<?php

namespace Tests\Feature\Candidates;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ManualGroupingTest extends TestCase
{
    use BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        $this->fakeAi(['classify' => self::aiError('unexpected')]);
    }

    private function topic(string $title, array $vector, array $attributes = [], ?int $workspaceId = null): Candidate
    {
        $candidate = $this->makeCandidate(['title' => $title, 'total_score' => 70, 'relevance_score' => 80, 'freshness_score' => 60,
            'search_potential_score' => 50, 'commercial_potential_score' => 40, 'category' => 'news', 'llm_reason' => 'Ocena AI.', ...$attributes], $workspaceId);
        DB::table('candidates')->where('id', $candidate->id)->update(['embedding' => '{'.implode(',', $vector).'}', 'embedding_model' => 'text-embedding-3-small']);

        return $candidate->refresh();
    }

    #[Test]
    public function similar_topics_are_listed_closest_first_within_the_account(): void
    {
        $mine = $this->topic('OpenAI wydało model', [1, 0, 0]);
        $close = $this->topic('Nowy model GPT', [0.8, 0.6, 0]);
        $far = $this->topic('Kubernetes', [0, 0, 1]);
        $this->topic('Obce konto', [1, 0, 0], [], $this->otherWorkspace()->id);

        $this->getJson("/api/candidates/{$mine->id}/similar")->assertOk()->assertJsonCount(2)
            ->assertJsonPath('0.id', $close->id)->assertJsonPath('0.similarity', 0.8)->assertJsonPath('1.id', $far->id);
        $this->getJson("/api/candidates/{$this->makeCandidate()->id}/similar")->assertOk()->assertJsonCount(0);
    }

    #[Test]
    public function a_topic_can_be_joined_to_another_group_for_free(): void
    {
        $primary = $this->topic('OpenAI wydało model', [1, 0, 0], ['total_score' => 90, 'covered_by' => ['type' => 'post', 'title' => 'Stary', 'post_id' => 5, 'url' => 'https://b.example/x', 'similarity' => 0.7]]);
        $member = $this->topic('Model od OpenAI', [0.9, 0.1, 0]);
        DB::table('candidates')->where('id', $member->id)->update(['topic_group_id' => $primary->id]);
        $mine = $this->topic('GPT-6 premiera', [0, 1, 0], ['total_score' => 20]);

        $this->postJson("/api/candidates/{$mine->id}/group", ['primary_id' => $member->id])->assertOk()
            ->assertJsonPath('topic_group_id', $primary->id)->assertJsonPath('total_score', 90)->assertJsonPath('covered_by.post_id', 5);

        $this->assertStringContainsString("#{$primary->id}", $mine->refresh()->llm_reason);
        $this->assertSame([], $this->aiRequests);
        $this->getJson('/api/candidates')->assertJsonPath('total', 1)->assertJsonPath('items.0.group_size', 3);
    }

    #[Test]
    public function invalid_joins_are_refused(): void
    {
        $primary = $this->topic('A', [1, 0, 0]);
        $member = $this->topic('B', [1, 0, 0]);
        DB::table('candidates')->where('id', $member->id)->update(['topic_group_id' => $primary->id]);
        $other = $this->topic('C', [0, 1, 0]);
        $unscored = $this->topic('D', [0, 0, 1], ['total_score' => null]);
        $foreign = $this->topic('E', [1, 0, 0], [], $this->otherWorkspace()->id);

        $this->postJson("/api/candidates/{$member->id}/group", ['primary_id' => $primary->id])->assertStatus(422);
        $this->postJson("/api/candidates/{$primary->id}/group", ['primary_id' => $other->id])->assertStatus(409)->assertJsonPath('detail.code', 'topic_has_members');
        $this->postJson("/api/candidates/{$other->id}/group", ['primary_id' => $unscored->id])->assertStatus(409)->assertJsonPath('detail.code', 'target_not_classified');
        $this->postJson("/api/candidates/{$other->id}/group", ['primary_id' => $foreign->id])->assertNotFound();
        $this->postJson("/api/candidates/{$other->id}/group", ['primary_id' => 'x'])->assertStatus(422);
        $this->makeJob(['status' => 'running'], $other);
        $this->postJson("/api/candidates/{$other->id}/group", ['primary_id' => $primary->id])->assertStatus(409)->assertJsonPath('detail.code', 'job_active');
    }

    #[Test]
    public function a_duplicate_can_be_separated_and_keeps_its_score(): void
    {
        $primary = $this->topic('A', [1, 0, 0]);
        $member = $this->topic('B', [1, 0, 0], ['total_score' => 70]);
        DB::table('candidates')->where('id', $member->id)->update(['topic_group_id' => $primary->id, 'duplicate_similarity' => 0.9]);

        $this->postJson("/api/candidates/{$member->id}/ungroup")->assertOk()->assertJsonPath('topic_group_id', null)->assertJsonPath('total_score', 70);

        $this->assertStringContainsString('Odłączono', $member->refresh()->llm_reason);
        $this->assertNull($member->duplicate_similarity);
        $this->postJson("/api/candidates/{$primary->id}/ungroup")->assertStatus(409)->assertJsonPath('detail.code', 'not_grouped');
        $this->getJson('/api/candidates')->assertJsonPath('total', 2);
    }
}
