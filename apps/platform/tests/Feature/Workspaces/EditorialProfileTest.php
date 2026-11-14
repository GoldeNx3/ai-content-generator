<?php

namespace Tests\Feature\Workspaces;

use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\Feature\Qa\QaPipelineTest;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class EditorialProfileTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private const PROFILE = [
        'audience' => 'Programiści PHP', 'voice' => 'Rzeczowo', 'topics_scope' => 'Laravel, DevOps',
        'banned_phrases' => ['rewolucja'], 'example_post' => '## Wzorzec',
    ];

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function the_profile_starts_empty_and_is_saved_per_account(): void
    {
        $this->getJson('/api/workspace/editorial')->assertOk()->assertExactJson([
            'audience' => '', 'voice' => '', 'topics_scope' => '', 'banned_phrases' => [], 'example_post' => '',
        ]);
        $other = Workspace::query()->create(['name' => 'inne']);

        $this->patchJson('/api/workspace/editorial', self::PROFILE)->assertOk()->assertJsonPath('audience', 'Programiści PHP');

        $this->getJson('/api/workspace/editorial')->assertJsonPath('banned_phrases', ['rewolucja']);
        $this->assertNull($other->fresh()->editorial_profile);
    }

    #[Test]
    public function invalid_profiles_are_rejected(): void
    {
        $this->patchJson('/api/workspace/editorial', ['example_post' => str_repeat('a', 6001)])->assertStatus(422);
        $this->patchJson('/api/workspace/editorial', ['banned_phrases' => array_fill(0, 51, 'x')])->assertStatus(422);
        $this->patchJson('/api/workspace/editorial', ['banned_phrases' => [str_repeat('a', 81)]])->assertStatus(422);
        $this->patchJson('/api/workspace/editorial', ['audience' => str_repeat('a', 501)])->assertStatus(422);
    }

    #[Test]
    public function classification_and_qa_receive_the_profile(): void
    {
        $this->patchJson('/api/workspace/editorial', self::PROFILE)->assertOk();
        $this->fakeAi([
            'classify' => self::aiOk(['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r']),
            'qa.evaluate' => QaPipelineTest::evaluation(),
        ]);

        $this->postJson("/api/candidates/{$this->makeCandidate()->id}/classify")->assertStatus(202);
        $this->postJson("/api/articles/{$this->makeArticle($this->makeCandidate())->id}/qa")->assertStatus(202);

        $requests = collect($this->aiRequests)->keyBy('task');
        $this->assertSame('Laravel, DevOps', $requests['classify']['input']['editorial']['topics_scope']);
        $this->assertSame(['rewolucja'], $requests['qa.evaluate']['input']['editorial']['banned_phrases']);
    }
}
