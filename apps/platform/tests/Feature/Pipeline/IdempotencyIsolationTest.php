<?php

namespace Tests\Feature\Pipeline;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Str;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Ramsey\Uuid\Uuid;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class IdempotencyIsolationTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        Queue::fake();
        Http::preventStrayRequests();
        Http::fake(['*' => Http::response('', 404)]);
    }

    private function foreignCandidate(): Candidate
    {
        return $this->makeCandidate([], $this->otherWorkspace()->id);
    }

    #[Test]
    public function the_same_key_in_two_accounts_creates_two_independent_jobs(): void
    {
        $key = (string) Str::uuid();
        $foreign = $this->makeJob(['idempotency_key' => $key], $this->foreignCandidate());

        $response = $this->postJson("/api/candidates/{$this->makeCandidate()->id}/classify", [], ['Idempotency-Key' => $key])->assertStatus(202);

        $this->assertNotSame($foreign->id, $response->json('id'));
        $this->assertStringNotContainsString($foreign->id, $response->getContent());
        $this->assertSame(2, PipelineJob::query()->where('idempotency_key', $key)->count());
    }

    #[Test]
    public function qa_retry_never_replays_a_job_of_another_account(): void
    {
        $key = (string) Str::uuid();
        $original = $this->makeJob(['kind' => 'qa_article', 'status' => 'failed'], $this->foreignCandidate());
        $foreign = $this->makeJob(['kind' => 'qa_article', 'idempotency_key' => $key, 'retry_of_job_id' => $original->id], $original->candidate);
        $article = $this->makeArticle($this->makeCandidate());

        $response = $this->postJson("/api/articles/{$article->id}/qa/retry", [], ['Idempotency-Key' => $key]);

        $this->assertNotSame(202, $response->status());
        $this->assertStringNotContainsString($foreign->id, $response->getContent());
    }

    #[Test]
    public function a_planted_scheduler_key_cannot_block_another_accounts_automation(): void
    {
        $candidate = $this->makeCandidate();
        $oldPredictableKey = Uuid::uuid5('6ba7b811-9dad-11d1-80b4-00c04fd430c8', "scheduled-classify:{$candidate->id}")->toString();
        $this->makeJob(['idempotency_key' => $oldPredictableKey], $this->foreignCandidate());
        Workspace::query()->whereKey($this->workspace->id)->update(['auto_fetch_enabled' => true, 'auto_classify_enabled' => true]);

        $this->artisan('pipeline:scheduled')->assertSuccessful();

        $this->assertSame(1, PipelineJob::query()->where('candidate_id', $candidate->id)->where('kind', 'classify')->count());
        $this->assertNotSame($oldPredictableKey, PipelineJob::query()->where('candidate_id', $candidate->id)->value('idempotency_key'));
    }
}
