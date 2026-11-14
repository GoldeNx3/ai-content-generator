<?php

namespace Tests\Feature\Architecture;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\RateLimiter;
use Modules\Candidates\Models\Candidate;
use Modules\Sources\Models\Source;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class AbuseLimitsTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function expensive_routes_are_throttled_per_account(): void
    {
        foreach (range(1, 10) as $_) {
            $this->postJson('/api/sources/fetch')->assertOk();
        }
        $this->postJson('/api/sources/fetch')->assertStatus(429)->assertJsonPath('detail.code', 'too_many_requests');
        $this->postJson('/api/candidates/classify-pending')->assertStatus(429);
    }

    #[Test]
    public function the_limit_of_one_account_does_not_affect_another(): void
    {
        foreach (range(1, 10) as $_) {
            RateLimiter::hit(md5('expensive'.'expensive:127.0.0.1'), 60);
            RateLimiter::hit(md5('expensive'.'expensive:'.($this->user->id + 1)), 60);
        }

        $this->postJson('/api/sources/fetch')->assertOk();
    }

    #[Test]
    public function an_account_cannot_add_more_than_200_sources(): void
    {
        DB::table('sources')->insert(array_map(fn (int $i) => ['workspace_id' => $this->workspace->id, 'name' => "S{$i}", 'url' => "https://example.com/{$i}.xml",
            'type' => 'rss', 'active' => true, 'created_at' => now(), 'updated_at' => now()], range(1, 200)));

        $this->postJson('/api/sources', ['name' => 'X', 'url' => 'https://example.com/x.xml'])->assertStatus(422)->assertJsonPath('detail.code', 'source_limit_reached');
        $this->assertSame(200, Source::query()->count());
    }

    #[Test]
    public function list_pages_are_bounded(): void
    {
        $candidate = Candidate::query()->create(['workspace_id' => $this->workspace->id,
            'source_id' => Source::query()->create(['workspace_id' => $this->workspace->id, 'name' => 'S', 'url' => 'https://example.com/a.xml'])->id,
            'external_url' => 'https://example.com/a', 'title' => 'T']);
        $this->getJson('/api/candidates?page=10001')->assertStatus(422);
        $this->getJson('/api/jobs?page=10001')->assertStatus(422);
        $this->getJson("/api/candidates/{$candidate->id}/jobs?page=10001")->assertStatus(422);
        $this->getJson('/api/candidates?page=10000')->assertOk();
    }
}
