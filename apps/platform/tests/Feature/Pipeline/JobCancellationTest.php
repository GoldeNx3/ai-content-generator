<?php

namespace Tests\Feature\Pipeline;

use Modules\Ai\Services\AiRunner;
use Modules\Pipeline\Commands\SucceedJobCommand;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Pipeline\Services\JobRunContext;
use Modules\Pipeline\Services\RunningJobWriter;
use Modules\Research\Enums\ResearchStatus;
use Modules\Research\Models\Research;
use Modules\Workspaces\Enums\WorkspaceRole;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class JobCancellationTest extends TestCase
{
    use BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    private static function extraction(string $url): array
    {
        return [
            'url' => $url, 'source_type' => 'news', 'source_score' => 70, 'fetch_status' => 'success', 'http_status' => 200,
            'error' => null, 'title' => 'Tytuł', 'publisher' => 'Wydawca', 'published_at' => '2026-06-01T00:00:00+00:00',
            'extracted_content' => 'Treść', 'raw_content' => '<p>raw</p>',
        ];
    }

    private function fakeResearchCancelledDuringExtract(): void
    {
        $this->fakeAi([
            'research.extract' => function (array $request) {
                PipelineJob::query()->where('status', JobStatus::Running->value)->update(['cancel_requested_at' => now()]);

                return self::aiOk(['sources' => array_map(fn ($url) => self::extraction($url), $request['input']['urls'])]);
            },
            'research.discover' => self::aiOk(['queries' => [], 'sources' => []]),
            'research.analyse' => self::aiOk(['summary' => 's']),
        ]);
    }

    private function aiTasks(): array
    {
        return array_column($this->aiRequests, 'task');
    }

    #[Test]
    public function cancelled_status_is_accepted_by_database(): void
    {
        $job = $this->makeJob();
        $job->forceFill(['status' => JobStatus::Cancelled])->save();

        $this->assertSame(JobStatus::Cancelled, $job->fresh()->status);
        $this->assertFalse(JobStatus::Cancelled->isActive());
    }

    #[Test]
    public function queued_job_is_cancelled_immediately(): void
    {
        $job = $this->makeJob(['status' => 'retrying', 'attempt_count' => 1]);

        $this->postJson("/api/jobs/{$job->id}/cancel")->assertOk()
            ->assertJsonPath('status', 'cancelled')->assertJsonPath('error.code', 'cancelled');

        $fresh = $job->fresh();
        $this->assertSame($this->user->id, $fresh->cancelled_by);
        $this->assertNotNull($fresh->finished_at);
    }

    #[Test]
    public function running_job_stops_before_next_paid_step(): void
    {
        $this->fakeResearchCancelledDuringExtract();
        $candidate = $this->makeCandidate();

        $jobId = $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202)->json('id');

        $job = PipelineJob::query()->find($jobId);
        $this->assertSame(JobStatus::Cancelled, $job->status);
        $this->assertSame('cancelled', $job->error_code);
        $this->assertSame(['research.extract'], $this->aiTasks());
        $this->assertSame('cancelled', PipelineJobAttempt::query()->where('pipeline_job_id', $jobId)->value('outcome'));
        $this->assertSame(ResearchStatus::Failed, Research::query()->where('candidate_id', $candidate->id)->value('status'));
    }

    #[Test]
    public function running_job_is_flagged_and_succeeds_without_further_ai_steps(): void
    {
        $job = $this->makeJob(['status' => 'running', 'attempt_count' => 1]);
        PipelineJobAttempt::query()->create(['pipeline_job_id' => $job->id, 'number' => 1, 'started_at' => now()]);

        $this->postJson("/api/jobs/{$job->id}/cancel")->assertStatus(202)->assertJsonPath('status', 'running');
        $this->assertNotNull($job->fresh()->cancel_requested_at);

        $context = new JobRunContext($job->fresh(), app(RunningJobWriter::class), app(SucceedJobCommand::class), app(AiRunner::class), 60);
        $context->finish(fn () => null);

        $this->assertSame(JobStatus::Succeeded, $job->fresh()->status);
    }

    #[Test]
    public function cancel_request_after_success_does_not_override_result(): void
    {
        $job = $this->makeJob(['status' => 'succeeded', 'finished_at' => now()]);

        $this->postJson("/api/jobs/{$job->id}/cancel")->assertStatus(409)->assertJsonPath('detail.code', 'job_not_cancellable');
        $this->assertSame(JobStatus::Succeeded, $job->fresh()->status);
        $this->assertNull($job->fresh()->cancel_requested_at);
    }

    #[Test]
    public function cancelled_research_can_be_enqueued_again(): void
    {
        $this->fakeResearchCancelledDuringExtract();
        $candidate = $this->makeCandidate();
        $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202);

        $queued = $this->makeJob(['kind' => 'research'], $this->makeCandidate());
        $this->postJson("/api/jobs/{$queued->id}/cancel")->assertOk();

        $this->fakeAi([]);
        $this->assertSame(0, PipelineJob::query()->whereIn('status', JobStatus::active())->count());
        $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202);
        $this->postJson("/api/candidates/{$queued->candidate_id}/research")->assertStatus(202);
    }

    #[Test]
    public function cancel_pending_only_touches_own_queued_jobs(): void
    {
        $this->makeJob();
        $this->makeJob(['status' => 'retrying', 'attempt_count' => 1]);
        $running = $this->makeJob(['status' => 'running', 'attempt_count' => 1]);
        $foreign = $this->makeJob([], $this->makeCandidate([], $this->otherWorkspace()->id));

        $this->postJson('/api/jobs/cancel-pending')->assertOk()->assertExactJson(['cancelled' => 2]);

        $this->assertSame(JobStatus::Running, $running->fresh()->status);
        $this->assertNull($running->fresh()->cancel_requested_at);
        $this->assertSame(JobStatus::Queued, $foreign->fresh()->status);
    }

    #[Test]
    public function members_cancel_single_jobs_but_not_all_pending(): void
    {
        $job = $this->makeJob();
        $this->signIn(WorkspaceRole::Member, $this->workspace);

        $this->postJson('/api/jobs/cancel-pending')->assertStatus(403)->assertJsonPath('detail.code', 'owner_required');
        $this->postJson("/api/jobs/{$job->id}/cancel")->assertOk()->assertJsonPath('status', 'cancelled');
    }

    #[Test]
    public function running_wordpress_publication_cannot_be_stopped_midway(): void
    {
        $running = $this->makeJob(['kind' => 'publish_wordpress', 'status' => 'running', 'attempt_count' => 1]);
        $queued = $this->makeJob(['kind' => 'publish_wordpress']);

        $this->postJson("/api/jobs/{$running->id}/cancel")->assertStatus(409)->assertJsonPath('detail.code', 'job_not_stoppable');
        $this->assertNull($running->fresh()->cancel_requested_at);
        $this->assertSame(JobStatus::Running, $running->fresh()->status);
        $this->postJson("/api/jobs/{$queued->id}/cancel")->assertOk()->assertJsonPath('status', 'cancelled');
    }

    #[Test]
    public function flagged_job_with_retryable_error_ends_cancelled_not_retrying(): void
    {
        $this->fakeAi([
            'research.extract' => function () {
                PipelineJob::query()->where('status', JobStatus::Running->value)->update(['cancel_requested_at' => now()]);

                return self::aiError('llm_http_503', retryable: true);
            },
        ]);
        $candidate = $this->makeCandidate();

        $jobId = $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202)->json('id');

        $job = PipelineJob::query()->find($jobId);
        $this->assertSame(JobStatus::Cancelled, $job->status);
        $this->assertSame(1, $job->attempt_count);
        $this->assertSame(['research.extract'], $this->aiTasks());
    }

    #[Test]
    public function candidate_jobs_can_be_filtered_by_cancelled(): void
    {
        $job = $this->makeJob(['status' => 'cancelled']);
        $this->makeJob(['status' => 'failed'], $job->candidate);

        $this->getJson("/api/candidates/{$job->candidate_id}/jobs?status=cancelled")->assertOk()
            ->assertJsonPath('total', 1)->assertJsonPath('items.0.id', $job->id);
    }

    #[Test]
    public function foreign_job_cannot_be_cancelled(): void
    {
        $foreign = $this->makeJob([], $this->makeCandidate([], $this->otherWorkspace()->id));

        $this->postJson("/api/jobs/{$foreign->id}/cancel")->assertNotFound();
        $this->assertSame(JobStatus::Queued, $foreign->fresh()->status);
    }
}
