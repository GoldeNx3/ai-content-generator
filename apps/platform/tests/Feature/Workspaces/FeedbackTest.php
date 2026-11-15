<?php

namespace Tests\Feature\Workspaces;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class FeedbackTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private const SUGGESTIONS = ['suggestions' => [
        ['kind' => 'style_rule', 'text' => 'Pierwsze zdanie podaje konkretny fakt z datą.', 'why' => 'Tak poprawiasz wstępy.'],
        ['kind' => 'banned_phrase', 'text' => 'w dzisiejszym dynamicznym świecie', 'why' => 'Usuwasz ten zwrot.'],
    ], 'passages' => 1];

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        $this->fakeAi(['feedback.suggest' => self::aiOk(self::SUGGESTIONS, [self::llmCall('learning_feedback', '0.002000')])]);
    }

    private function editedTopic(): Candidate
    {
        $candidate = $this->makeCandidate(['title' => 'Laravel 13']);
        $this->makeArticle($candidate, ['is_edited' => true, 'generated_content' => "## A\n\nW dzisiejszym dynamicznym świecie.", 'content' => "## A\n\nLaravel 13 wyszedł we wtorek."]);

        return $candidate;
    }

    #[Test]
    public function edits_and_rejection_reasons_are_analysed_as_a_paid_step_and_stored_as_suggestions(): void
    {
        $this->patchJson('/api/workspace/editorial', ['banned_phrases' => ['game changer']])->assertOk();
        $candidate = $this->editedTopic();
        $this->makeArticle($candidate, ['version' => 2, 'is_current' => false, 'status' => 'rejected', 'rejection_reason' => 'Za dużo ogólników.']);

        $this->postJson("/api/candidates/{$candidate->id}/feedback")->assertStatus(202)->assertJsonPath('kind', 'learn_feedback');

        $input = collect($this->aiRequests)->firstWhere('task', 'feedback.suggest')['input'];
        $this->assertSame('Laravel 13', $input['title']);
        $this->assertSame("## A\n\nW dzisiejszym dynamicznym świecie.", $input['original']);
        $this->assertSame("## A\n\nLaravel 13 wyszedł we wtorek.", $input['edited']);
        $this->assertSame(['Za dużo ogólników.'], $input['rejections']);
        $this->assertSame(['game changer'], $input['editorial']['banned_phrases']);
        $this->getJson("/api/candidates/{$candidate->id}/suggestions")->assertOk()->assertJsonCount(2)
            ->assertJsonPath('0.kind', 'style_rule')->assertJsonPath('0.status', 'pending')
            ->assertJsonPath('1.text', 'w dzisiejszym dynamicznym świecie');
        $this->getJson('/api/usage/report')->assertJsonPath('by_kind.0.kind', 'learn_feedback')->assertJsonPath('by_kind.0.cost_usd', '0.002000');
    }

    #[Test]
    public function a_topic_without_edits_or_rejection_reasons_cannot_be_analysed(): void
    {
        $candidate = $this->makeCandidate();
        $this->makeArticle($candidate);

        $this->postJson("/api/candidates/{$candidate->id}/feedback")->assertStatus(422);
        $this->assertSame([], $this->aiRequests);
    }

    #[Test]
    public function accepted_suggestions_join_the_profile_and_dismissed_ones_do_not(): void
    {
        $candidate = $this->editedTopic();
        $this->postJson("/api/candidates/{$candidate->id}/feedback")->assertStatus(202);
        [$rule, $phrase] = $this->getJson("/api/candidates/{$candidate->id}/suggestions")->json();

        $this->postJson("/api/suggestions/{$rule['id']}/accept")->assertOk()->assertJsonPath('status', 'accepted');
        $this->postJson("/api/suggestions/{$rule['id']}/accept")->assertOk();
        $this->postJson("/api/suggestions/{$phrase['id']}/dismiss")->assertOk()->assertJsonPath('status', 'dismissed');

        $this->getJson('/api/workspace/editorial')->assertJsonPath('style_rules', ['Pierwsze zdanie podaje konkretny fakt z datą.'])
            ->assertJsonPath('banned_phrases', []);
        $this->postJson("/api/suggestions/{$phrase['id']}/accept")->assertOk();
        $this->getJson('/api/workspace/editorial')->assertJsonPath('banned_phrases', ['w dzisiejszym dynamicznym świecie']);
    }

    #[Test]
    public function a_full_profile_rejects_more_rules(): void
    {
        $this->patchJson('/api/workspace/editorial', ['style_rules' => array_map(fn (int $i) => "Zasada {$i}", range(1, 30))])->assertOk();
        $candidate = $this->editedTopic();
        $this->postJson("/api/candidates/{$candidate->id}/feedback")->assertStatus(202);
        $rule = $this->getJson("/api/candidates/{$candidate->id}/suggestions")->json('0');

        $this->postJson("/api/suggestions/{$rule['id']}/accept")->assertStatus(409);
        $this->assertSame('pending', DB::table('editorial_suggestions')->where('id', $rule['id'])->value('status'));
    }

    #[Test]
    public function style_rules_are_validated_and_reach_the_writer(): void
    {
        $this->patchJson('/api/workspace/editorial', ['style_rules' => array_fill(0, 31, 'x')])->assertStatus(422);
        $this->patchJson('/api/workspace/editorial', ['style_rules' => [str_repeat('a', 201)]])->assertStatus(422);
        $this->patchJson('/api/workspace/editorial', ['style_rules' => ['  Krótkie akapity.  ', 'Krótkie akapity.']])->assertOk()
            ->assertJsonPath('style_rules', ['Krótkie akapity.']);
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate();
        $this->completedResearch($candidate);

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $this->assertSame(['Krótkie akapity.'], collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['editorial']['style_rules']);
    }

    #[Test]
    public function suggestions_of_another_account_are_not_found(): void
    {
        $foreign = $this->makeCandidate([], $this->otherWorkspace()->id);
        $id = DB::table('editorial_suggestions')->insertGetId(['workspace_id' => $foreign->workspace_id, 'candidate_id' => $foreign->id,
            'kind' => 'style_rule', 'text' => 'x', 'why' => 'y', 'status' => 'pending', 'created_at' => now(), 'updated_at' => now()]);

        $this->postJson("/api/suggestions/{$id}/accept")->assertNotFound();
        $this->getJson("/api/candidates/{$foreign->id}/suggestions")->assertNotFound();
    }
}
