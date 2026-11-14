<?php

namespace Tests\Feature\Candidates;

use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class EditorTakeTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function the_editor_take_is_saved_shown_and_limited(): void
    {
        $candidate = $this->makeCandidate();

        $this->patchJson("/api/candidates/{$candidate->id}/editor-take", ['editor_take' => '  Używamy tego w 3 projektach.  '])->assertOk()
            ->assertJsonPath('editor_take', 'Używamy tego w 3 projektach.');
        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('editor_take', 'Używamy tego w 3 projektach.');
        $this->patchJson("/api/candidates/{$candidate->id}/editor-take", ['editor_take' => str_repeat('a', 3001)])->assertStatus(422);
        $this->patchJson("/api/candidates/{$candidate->id}/editor-take", ['editor_take' => null])->assertOk()->assertJsonPath('editor_take', null);

        $foreign = $this->makeCandidate([], $this->otherWorkspace()->id);
        $this->patchJson("/api/candidates/{$foreign->id}/editor-take", ['editor_take' => 'x'])->assertNotFound();
    }

    #[Test]
    public function article_generation_hands_the_take_to_the_brief(): void
    {
        $this->fakeAi(['article.brief' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate();
        $this->completedResearch($candidate);
        $this->patchJson("/api/candidates/{$candidate->id}/editor-take", ['editor_take' => 'Nasza opinia.'])->assertOk();

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $this->assertSame('Nasza opinia.', collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['editor_take']);
    }
}
