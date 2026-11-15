<?php

namespace Tests\Feature\Usage;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\Candidates\Models\Candidate;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class CostReportTest extends TestCase
{
    use BuildsArticles, BuildsDomain;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
        CarbonImmutable::setTestNow('2026-11-20 12:00:00');
    }

    private function attempt(Candidate $candidate, string $kind, array $calls, string $startedAt = '2026-11-10 10:00:00'): void
    {
        $job = $this->makeJob(['kind' => $kind, 'status' => 'succeeded'], $candidate);
        DB::table('pipeline_job_attempts')->insert(['pipeline_job_id' => $job->id, 'number' => 1, 'started_at' => $startedAt,
            'outcome' => 'succeeded', 'llm_calls' => json_encode($calls)]);
    }

    private static function llm(string $stage, ?string $cost, bool $finished = true): array
    {
        return ['stage' => $stage, 'finished' => $finished, 'estimated_cost_usd' => $cost];
    }

    #[Test]
    public function the_month_is_split_by_step_and_by_call_stage(): void
    {
        $written = $this->makeCandidate();
        $this->makeArticle($written);
        $this->attempt($written, 'research', [self::llm('discovering_sources', '0.001000'), self::llm('searching_sources', '0.016000'), self::llm('analysing', '0.010000')]);
        $this->attempt($written, 'write', [self::llm('building_brief', '0.002000'), self::llm('writing', '0.020000'), self::llm('embedding', '0.000001')]);
        $skipped = $this->makeCandidate();
        $this->attempt($skipped, 'classify', [self::llm('embedding', '0.000001'), self::llm('classifying', '0.000500')]);
        $this->attempt($skipped, 'classify', [self::llm('classifying', null, false)]);
        $this->attempt($skipped, 'classify', [self::llm('classifying', '9.000000')], '2026-10-31 23:59:59');
        $this->attempt($this->makeCandidate([], $this->otherWorkspace()->id), 'write', [self::llm('writing', '5.000000')]);

        $report = $this->getJson('/api/usage/report?month=2026-11')->assertOk()->json();

        $this->assertSame('2026-11', $report['month']);
        $this->assertSame('0.049502', $report['total_usd']);
        $this->assertSame(1, $report['unknown_cost_calls']);
        $this->assertSame(['kind' => 'research', 'jobs' => 1, 'cost_usd' => '0.027000'], $report['by_kind'][0]);
        $this->assertSame(['kind' => 'write', 'jobs' => 1, 'cost_usd' => '0.022001'], $report['by_kind'][1]);
        $this->assertSame(['kind' => 'classify', 'jobs' => 2, 'cost_usd' => '0.000501'], collect($report['by_kind'])->firstWhere('kind', 'classify'));
        $this->assertSame(['stage' => 'searching_sources', 'calls' => 1, 'cost_usd' => '0.016000'], collect($report['by_stage'])->firstWhere('stage', 'searching_sources'));
        $this->assertSame(['stage' => 'embedding', 'calls' => 2, 'cost_usd' => '0.000002'], collect($report['by_stage'])->firstWhere('stage', 'embedding'));
        $this->assertSame(['topics' => 1, 'cost_usd' => '0.049001', 'average_usd' => '0.049001'], $report['articles']);
    }

    #[Test]
    public function the_current_month_is_the_default_and_bad_months_are_rejected(): void
    {
        $this->getJson('/api/usage/report')->assertOk()->assertJsonPath('month', '2026-11')->assertJsonPath('total_usd', '0.000000')
            ->assertJsonPath('articles.average_usd', null);
        $this->getJson('/api/usage/report?month=2026-13')->assertStatus(422);
        $this->getJson('/api/usage/report?month=listopad')->assertStatus(422);
    }
}
