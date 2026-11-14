<?php

namespace Tests\Feature\Pipeline;

use Illuminate\Support\Facades\Queue;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunner;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class WorkerBudgetTest extends TestCase
{
    use BuildsDomain, FakesAi;

    private const SCORES = ['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'];

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        $this->fakeAi(['classify' => self::aiOk(self::SCORES, [self::llmCall('classifying', '5.000000')])]);
    }

    #[Test]
    public function queued_paid_job_does_not_call_ai_once_the_budget_is_spent(): void
    {
        Workspace::query()->whereKey($this->workspace->id)->update(['monthly_budget_usd' => '5.00']);
        Queue::fake();
        $first = PipelineJob::query()->findOrFail($this->postJson("/api/candidates/{$this->makeCandidate()->id}/classify")->assertStatus(202)->json('id'));
        $second = PipelineJob::query()->findOrFail($this->postJson("/api/candidates/{$this->makeCandidate()->id}/classify")->assertStatus(202)->json('id'));
        app(JobRunner::class)->run($first->id);
        $this->assertSame(JobStatus::Succeeded, $first->fresh()->status, (string) $first->fresh()->error_message);

        app(JobRunner::class)->run($second->id);

        $this->assertSame(JobStatus::Failed, $second->fresh()->status);
        $this->assertSame('budget_exceeded', $second->fresh()->error_code);
        $this->assertCount(1, $this->aiRequests);
    }

    #[Test]
    public function classify_pending_limit_matches_the_workspace_cap(): void
    {
        $this->postJson('/api/candidates/classify-pending', ['limit' => 201])->assertStatus(422);
        $this->postJson('/api/candidates/classify-pending', ['limit' => 200])->assertStatus(202);
    }

    #[Test]
    public function registration_is_closed_by_default(): void
    {
        $this->assertStringContainsString("env('ALLOW_REGISTRATION', false)", file_get_contents(base_path('config/content.php')));
        foreach ([base_path('.env.example')] as $example) {
            $this->assertMatchesRegularExpression('/^ALLOW_REGISTRATION=false$/m', file_get_contents($example), $example);
        }
    }
}
