<?php

namespace Tests\Feature\Demo;

use Modules\Articles\Models\Article;
use Modules\Candidates\Models\Candidate;
use Modules\Demo\Services\DemoSeedService;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Sources\Models\Source;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class DemoResetTest extends TestCase
{
    use BuildsDomain;

    #[Test]
    public function requires_a_session(): void
    {
        $this->spa()->postJson('/api/demo/reset')->assertStatus(401);
    }

    #[Test]
    public function creates_demo_topics_when_none_exist(): void
    {
        $this->signIn();

        $this->spa()->postJson('/api/demo/reset')->assertCreated()->assertExactJson(['removed' => 0, 'created' => 3]);

        $this->assertSame(3, Candidate::query()->where('workspace_id', $this->workspace->id)->count());
        $this->assertSame(1, Source::query()->where('url', DemoSeedService::sourceUrl())->count());
    }

    #[Test]
    #[Group('python')]
    public function replaces_used_demo_topics_and_touches_nothing_else(): void
    {
        $this->signIn();
        $this->artisan('demo:seed', ['--workspace' => $this->workspace->id]);
        $demo = Candidate::query()->where('external_url', Candidate::DEMO_PREFIX.'cases/discovered')->firstOrFail();
        $this->runDemoPipeline($demo);
        $this->assertGreaterThan(1, Article::query()->where('candidate_id', $demo->id)->count());

        $real = $this->makeCandidate(['title' => 'Prawdziwy temat']);
        $real->update(['topic_group_id' => $demo->id]);
        $other = $this->otherWorkspace();
        app(DemoSeedService::class)->seed($other->id);
        $oldIds = Candidate::query()->where('workspace_id', $this->workspace->id)->where('external_url', 'like', Candidate::DEMO_PREFIX.'%')->pluck('id')->all();

        $this->spa()->postJson('/api/demo/reset')->assertCreated()->assertExactJson(['removed' => 3, 'created' => 3]);

        $fresh = Candidate::query()->where('workspace_id', $this->workspace->id)->where('external_url', 'like', Candidate::DEMO_PREFIX.'%')->get();
        $this->assertCount(3, $fresh);
        $this->assertSame([], array_intersect($oldIds, $fresh->pluck('id')->all()), 'demo topics are recreated, not kept');
        $this->assertSame(['ignored', 'pending', 'pending'], $fresh->pluck('status')->map(fn ($status) => $status instanceof \BackedEnum ? $status->value : $status)->sort()->values()->all());
        $this->assertSame(0, Article::query()->whereIn('candidate_id', $oldIds)->count());
        $this->assertSame(0, PipelineJob::query()->whereIn('candidate_id', $oldIds)->count());
        $this->assertNull($fresh->firstWhere('external_url', Candidate::DEMO_PREFIX.'cases/discovered')->total_score);

        $this->assertNull($real->fresh()->topic_group_id, 'a real topic survives and is detached from the removed demo');
        $this->assertSame(3, Candidate::query()->where('workspace_id', $other->id)->count(), 'other accounts keep their demo topics');
        $this->getJson('/api/usage')->assertJsonPath('spent_usd', '0.000000');
    }

    #[Test]
    public function refuses_while_a_demo_job_is_active(): void
    {
        $this->signIn();
        app(DemoSeedService::class)->seed($this->workspace->id);
        $demo = Candidate::query()->where('external_url', Candidate::DEMO_PREFIX.'cases/discovered')->firstOrFail();
        $this->makeJob(['kind' => 'classify', 'status' => 'running'], $demo);

        $this->spa()->postJson('/api/demo/reset')->assertStatus(409)->assertExactJson(['detail' => ['code' => 'demo_jobs_active']]);

        $this->assertTrue(Candidate::query()->whereKey($demo->id)->exists());
    }

    private function runDemoPipeline(Candidate $candidate): void
    {
        $this->postJson("/api/candidates/{$candidate->id}/classify");
        $this->postJson("/api/candidates/{$candidate->id}/research");
        $this->postJson("/api/candidates/{$candidate->id}/article", ['length' => 'auto']);
        $article = Article::query()->where('candidate_id', $candidate->id)->firstOrFail();
        $this->postJson("/api/articles/{$article->id}/qa");
        $this->postJson("/api/article-versions/{$article->id}/auto-fix");
        $child = Article::query()->where('candidate_id', $candidate->id)->where('created_by', 'auto_fix')->firstOrFail();
        $this->postJson("/api/articles/{$child->id}/qa");
        $this->postJson("/api/article-versions/{$child->id}/approve")->assertOk();
    }
}
