<?php

namespace Tests\Feature\Workspaces;

use Illuminate\Support\Facades\Process;
use Illuminate\Support\Facades\Queue;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobStatus;
use Modules\Pipeline\Jobs\RunPipelineJob;
use Modules\Pipeline\Services\JobRunner;
use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class WorkspacePauseTest extends TestCase
{
    use BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function paused_workspace_jobs_are_not_claimed(): void
    {
        $this->fakeAi(['classify' => self::aiOk(['total_score' => 1])]);
        $queued = $this->makeJob();
        $retrying = $this->makeJob(['status' => 'retrying', 'attempt_count' => 1, 'available_at' => now()->subMinute()]);

        $this->postJson('/api/workspace/pause')->assertOk()->assertJsonStructure(['paused_at']);
        app(JobRunner::class)->run($queued->id);
        app(JobRunner::class)->run($retrying->id);

        $this->assertSame(JobStatus::Queued, $queued->fresh()->status);
        $this->assertSame(0, $queued->fresh()->attempt_count);
        $this->assertSame(JobStatus::Retrying, $retrying->fresh()->status);
        $this->assertSame(1, $retrying->fresh()->attempt_count);
        Process::assertNothingRan();
    }

    #[Test]
    public function recover_skips_paused_workspaces(): void
    {
        $this->makeJob(['available_at' => now()->subMinutes(10)]);
        $this->postJson('/api/workspace/pause')->assertOk();
        Queue::fake();

        $this->artisan('pipeline:recover')->assertSuccessful();

        Queue::assertNotPushed(RunPipelineJob::class);
    }

    #[Test]
    public function enqueue_is_rejected_while_paused(): void
    {
        $candidate = $this->makeCandidate();
        $demo = $this->makeCandidate(['external_url' => Candidate::DEMO_PREFIX.'pause']);
        $this->postJson('/api/workspace/pause')->assertOk();

        $this->postJson("/api/candidates/{$candidate->id}/classify")->assertStatus(409)->assertJsonPath('detail.code', 'workspace_paused');
        $this->postJson("/api/candidates/{$demo->id}/classify")->assertStatus(409)->assertJsonPath('detail.code', 'workspace_paused');
    }

    #[Test]
    public function resume_dispatches_waiting_jobs(): void
    {
        $this->makeJob();
        $this->makeJob();
        $this->postJson('/api/workspace/pause')->assertOk();
        Queue::fake();

        $this->postJson('/api/workspace/resume')->assertOk()->assertExactJson(['paused_at' => null, 'resumed_jobs' => 2]);

        Queue::assertPushed(RunPipelineJob::class, 2);
        $this->assertNull(Workspace::query()->find($this->workspace->id)->paused_at);
    }

    #[Test]
    public function only_owner_can_pause_and_other_workspaces_are_untouched(): void
    {
        $other = $this->otherWorkspace();
        $this->signIn(WorkspaceRole::Member);

        $this->postJson('/api/workspace/pause')->assertStatus(403)->assertJsonPath('detail.code', 'owner_required');
        $this->postJson('/api/workspace/resume')->assertStatus(403);
        $this->assertSame(0, Workspace::query()->whereNotNull('paused_at')->count());
        $this->assertNull($other->fresh()->paused_at);
    }
}
