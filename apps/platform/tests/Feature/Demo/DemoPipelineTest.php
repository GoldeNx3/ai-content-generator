<?php

namespace Tests\Feature\Demo;

use Modules\Articles\Models\Article;
use Modules\Candidates\Models\Candidate;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

#[Group('python')]
final class DemoPipelineTest extends TestCase
{
    #[Test]
    public function demo_seed_is_idempotent(): void
    {
        $this->signIn();
        $this->artisan('demo:seed', ['--workspace' => $this->workspace->id])->assertSuccessful();
        $this->artisan('demo:seed', ['--workspace' => $this->workspace->id])->assertSuccessful();

        $this->assertSame(3, Candidate::query()->count());
        $this->assertSame(1, Candidate::query()->where('status', 'ignored')->count());
    }

    #[Test]
    public function full_demo_pipeline_runs_through_real_python_without_cost(): void
    {
        $this->signIn();
        $this->artisan('demo:seed', ['--workspace' => $this->workspace->id]);
        $candidate = Candidate::query()->where('external_url', Candidate::DEMO_PREFIX.'cases/discovered')->firstOrFail();

        $classify = $this->postJson("/api/candidates/{$candidate->id}/classify")->json('id');
        $this->getJson("/api/jobs/{$classify}")->assertJsonPath('status', 'succeeded');
        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('total_score', 84)->assertJsonPath('llm_model', 'demo-static');

        $research = $this->postJson("/api/candidates/{$candidate->id}/research")->json('id');
        $this->getJson("/api/jobs/{$research}")->assertJsonPath('status', 'succeeded');
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonPath('status', 'completed')->assertJsonCount(3, 'facts');

        $write = $this->postJson("/api/candidates/{$candidate->id}/article", ['length' => 'auto'])->json('id');
        $this->getJson("/api/jobs/{$write}")->assertJsonPath('status', 'succeeded');
        $article = Article::query()->where('candidate_id', $candidate->id)->firstOrFail();

        $qa = $this->postJson("/api/articles/{$article->id}/qa")->json('id');
        $this->getJson("/api/jobs/{$qa}")->assertJsonPath('status', 'succeeded');
        $report = $this->getJson("/api/articles/{$article->id}/qa")->assertJsonPath('status', 'completed')->json();
        $this->assertFalse($report['qa_passed']);

        $fix = $this->postJson("/api/article-versions/{$article->id}/auto-fix")->json('id');
        $this->getJson("/api/jobs/{$fix}")->assertJsonPath('status', 'succeeded');
        $child = Article::query()->where('candidate_id', $candidate->id)->where('created_by', 'auto_fix')->firstOrFail();

        $this->postJson("/api/articles/{$child->id}/qa");
        $this->getJson("/api/articles/{$child->id}/qa")->assertJsonPath('qa_passed', true);
        $this->postJson("/api/article-versions/{$child->id}/approve")->assertOk()->assertJsonPath('status', 'approved');
        $this->getJson('/api/usage')->assertJsonPath('spent_usd', '0.000000');
    }
}
