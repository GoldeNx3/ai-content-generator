<?php

namespace Tests\Feature\Pipeline;

use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Str;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Services\JobRunner;
use Modules\Pipeline\Models\PipelineJobAttempt;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ClassificationPipelineTest extends TestCase
{
    use BuildsDomain, FakesAi;

    private const SCORES = ['relevance' => 90, 'freshness' => 80, 'search_potential' => 70, 'commercial_potential' => 60, 'total_score' => 79, 'category' => 'news', 'reason' => 'Uzasadnienie'];

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function classify_runs_python_and_stores_scores_and_cost(): void
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES, [self::llmCall('classifying', '0.000720', 'gpt-4.1-mini')])]);
        $candidate = $this->makeCandidate(['summary' => 'Opis']);

        $response = $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(202)
            ->assertJsonPath('kind', 'classify')->assertJsonPath('candidate_id', $candidate->id);
        $jobId = $response->json('id');
        $response->assertHeader('Location', "/api/jobs/{$jobId}");

        $this->getJson("/api/jobs/{$jobId}")->assertOk()->assertJsonPath('status', 'succeeded')
            ->assertJsonPath('result', ['type' => 'candidate', 'id' => $candidate->id])->assertJsonPath('attempt_count', 1);
        $this->getJson("/api/candidates/{$candidate->id}")
            ->assertJsonPath('total_score', 79)->assertJsonPath('category', 'news')
            ->assertJsonPath('llm_model', 'gpt-4.1-mini')->assertJsonPath('estimated_cost_usd', '0.000720');
        $this->assertSame('classify', $this->aiRequests[0]['task']);
        $this->assertFalse($this->aiRequests[0]['demo']);
        $this->assertSame('Opis', $this->aiRequests[0]['input']['candidate']['summary']);
        $this->getJson("/api/jobs/{$jobId}/attempts")->assertJsonPath('0.outcome', 'succeeded')
            ->assertJsonPath('0.llm_calls.0.estimated_cost_usd', '0.000720');
    }

    #[Test]
    public function retryable_error_schedules_retry_until_max_attempts(): void
    {
        Queue::fake();
        $this->fakeAi(['classify' => self::aiError('llm_http_503', retryable: true, calls: [['stage' => 'classifying', 'finished' => false, 'estimated_cost_usd' => null]])]);
        $candidate = $this->makeCandidate();
        $jobId = $this->postJson("/api/candidates/{$candidate->id}/classify")->json('id');
        Queue::assertPushed(RunPipelineJob::class, 1);

        app(JobRunner::class)->run($jobId);
        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'retrying')->assertJsonPath('error_code', 'llm_http_503');
        Queue::assertPushed(RunPipelineJob::class, 2);

        app(JobRunner::class)->run($jobId);
        app(JobRunner::class)->run($jobId);
        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'failed')->assertJsonPath('attempt_count', 3);
        $this->assertSame(3, PipelineJobAttempt::query()->count());
        $this->getJson('/api/usage')->assertJsonPath('unknown_cost_calls', 3);
    }

    #[Test]
    public function permanent_error_fails_immediately(): void
    {
        $this->fakeAi(['classify' => self::aiError('llm_http_401')]);
        $candidate = $this->makeCandidate();
        $jobId = $this->postJson("/api/candidates/{$candidate->id}/classify")->json('id');

        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'failed')
            ->assertJsonPath('error.code', 'llm_http_401')->assertJsonPath('error_message', 'Błąd llm_http_401');
    }

    #[Test]
    public function idempotency_key_returns_same_job_and_detects_conflicts(): void
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $candidate = $this->makeCandidate();
        $key = (string) Str::uuid();

        $first = $this->postJson("/api/candidates/{$candidate->id}/classify", [], ['Idempotency-Key' => $key])->json('id');
        $again = $this->postJson("/api/candidates/{$candidate->id}/classify", [], ['Idempotency-Key' => $key])->json('id');
        $this->assertSame($first, $again);
        $this->assertSame(1, PipelineJob::query()->count());

        $other = $this->makeCandidate();
        $this->postJson("/api/candidates/{$other->id}/classify", [], ['Idempotency-Key' => $key])
            ->assertStatus(409)->assertJsonPath('detail.code', 'idempotency_conflict')->assertJsonPath('detail.job_id', $first);
        $this->postJson("/api/candidates/{$other->id}/classify", [], ['Idempotency-Key' => 'nope'])->assertStatus(422);
    }

    #[Test]
    public function only_one_active_job_per_candidate(): void
    {
        $candidate = $this->makeCandidate();
        $active = PipelineJob::query()->create([
            'workspace_id' => $this->workspace->id, 'candidate_id' => $candidate->id, 'kind' => 'classify', 'status' => 'running',
            'payload' => [], 'idempotency_key' => (string) Str::uuid(), 'request_hash' => 'other',
        ]);

        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(409)
            ->assertExactJson(['detail' => ['code' => 'candidate_busy', 'job_id' => $active->id]]);
    }

    #[Test]
    public function budget_and_missing_api_key_block_paid_jobs_but_not_demo(): void
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $this->workspace->update(['monthly_budget_usd' => '0']);
        $candidate = $this->makeCandidate();
        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(402)->assertExactJson(['detail' => 'budget_exceeded']);

        $demo = $this->makeCandidate(['external_url' => Candidate::DEMO_PREFIX.'checks/1']);
        $this->postJson("/api/candidates/{$demo->id}/classify")->assertStatus(202);
        $this->assertTrue($this->aiRequests[0]['demo']);

        $this->workspace->update(['monthly_budget_usd' => null]);
        config(['content.ai.openai_api_key' => '']);
        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(503)->assertExactJson(['detail' => 'OPENAI_API_KEY is not set']);
    }

    #[Test]
    public function classify_pending_batches_unclassified_candidates_of_workspace(): void
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $this->makeCandidate();
        $this->makeCandidate();
        $this->makeCandidate(['total_score' => 50]);
        $this->makeCandidate([], $this->otherWorkspace()->id);
        $key = (string) Str::uuid();

        $this->postJson('/api/candidates/classify-pending', [], ['Idempotency-Key' => $key])->assertStatus(202)
            ->assertJsonPath('enqueued', 2)->assertJsonPath('existing', 0)->assertJsonPath('skipped_budget', 0);
        $this->postJson('/api/candidates/classify-pending', [], ['Idempotency-Key' => $key])
            ->assertJsonPath('enqueued', 0)->assertJsonPath('existing', 2);
        $this->assertSame(2, PipelineJob::query()->count());
    }

    #[Test]
    public function queue_endpoints_list_stats_and_retry(): void
    {
        $this->fakeAi(['classify' => self::aiError('invalid_output')]);
        $candidate = $this->makeCandidate(['title' => 'Kolejka']);
        $jobId = $this->postJson("/api/candidates/{$candidate->id}/classify")->json('id');

        $this->getJson('/api/jobs?status=all')->assertJsonPath('total', 1)->assertJsonPath('items.0.candidate_title', 'Kolejka');
        $this->getJson('/api/jobs')->assertJsonPath('total', 0);
        $this->getJson('/api/jobs/stats')->assertExactJson(['queued' => 0, 'running' => 0, 'retrying' => 0, 'succeeded' => 0, 'failed' => 1, 'total' => 1]);
        $this->getJson("/api/candidates/{$candidate->id}/jobs")->assertJsonPath('total', 1);

        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $retry = $this->postJson("/api/jobs/{$jobId}/retry")->assertStatus(202)->json('id');
        $this->assertNotSame($jobId, $retry);
        $this->getJson("/api/jobs/{$retry}")->assertJsonPath('status', 'succeeded');
        $this->postJson("/api/jobs/{$retry}/retry")->assertStatus(409)->assertJsonPath('detail.code', 'job_not_failed');
    }

    #[Test]
    public function recover_command_retries_lost_jobs(): void
    {
        $this->fakeAi(['classify' => self::aiOk(self::SCORES)]);
        $candidate = $this->makeCandidate();
        $job = PipelineJob::query()->create([
            'workspace_id' => $this->workspace->id, 'candidate_id' => $candidate->id, 'kind' => 'classify', 'status' => 'running',
            'attempt_count' => 1, 'lease_expires_at' => now()->subMinute(), 'payload' => ['candidate_input' => ['title' => 'x', 'source' => 's']],
            'idempotency_key' => (string) Str::uuid(), 'request_hash' => 'x',
        ]);
        PipelineJobAttempt::query()->create(['pipeline_job_id' => $job->id, 'number' => 1]);

        $this->artisan('pipeline:recover')->assertSuccessful();

        $this->assertSame('succeeded', $job->refresh()->status->value);
        $this->assertSame('interrupted', PipelineJobAttempt::query()->where('number', 1)->value('outcome'));
    }
}
