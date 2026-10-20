<?php

namespace Tests\Feature\Qa;

use Modules\Qa\Models\ArticleQa;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class QaPipelineTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    public static function evaluation(int $score = 92, array $issues = [], bool $passed = true): array
    {
        return self::aiOk([
            'factual_score' => $score, 'source_score' => $score, 'style_score' => $score, 'structure_score' => $score, 'seo_score' => $score,
            'overall_score' => $score, 'supported_claims_count' => 3, 'unsupported_claims_count' => $passed ? 0 : 1,
            'critical_issue_count' => 0, 'warning_count' => count($issues), 'qa_passed' => $passed,
            'summary' => 'Raport', 'claims' => [], 'issues' => $issues,
        ], [self::llmCall('fact_checking', '0.003000', 'gpt-qa')]);
    }

    public static function issue(array $overrides = []): array
    {
        return ['type' => 'unsupported_claim', 'severity' => 'high', 'excerpt' => 'Nexa zwiększa produktywność o 47%.',
            'reason' => 'Brak źródła', 'suggestion' => 'Usuń', 'section_heading' => 'Sekcja', 'fact_ids' => [], 'source_ids' => [],
            'auto_fixable' => true, ...$overrides];
    }

    #[Test]
    public function passing_qa_makes_version_ready_and_approvable(): void
    {
        $this->fakeAi(['qa.evaluate' => self::evaluation()]);
        $candidate = $this->makeCandidate();
        $article = $this->makeArticle($candidate);

        $this->getJson("/api/articles/{$article->id}/qa")->assertNotFound()->assertExactJson(['detail' => 'QA report not found']);
        $job = $this->postJson("/api/articles/{$article->id}/qa")->assertStatus(202)->assertJsonPath('article_id', $article->id)->json('id');

        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'succeeded');
        $this->getJson("/api/articles/{$article->id}/qa")->assertOk()->assertJsonPath('status', 'completed')
            ->assertJsonPath('overall_score', 92)->assertJsonPath('qa_passed', true)->assertJsonPath('is_stale', false)
            ->assertJsonPath('estimated_cost_usd', '0.003000')->assertJsonPath('llm_model', 'gpt-qa');
        $this->getJson("/api/articles/{$article->id}")->assertJsonPath('status', 'ready_for_approval')
            ->assertJsonPath('qa_status', 'completed')->assertJsonPath('qa_score', 92);
        $snapshot = $this->aiRequests[0]['input']['snapshot'];
        $this->assertSame($article->id, $snapshot['article_id']);
        $this->assertSame(85, $this->aiRequests[0]['input']['pass_score']);

        $this->postJson("/api/article-versions/{$article->id}/approve")->assertOk()->assertJsonPath('status', 'approved');
        $this->getJson("/api/candidates/{$candidate->id}")->assertJsonPath('workflow_status', 'approved');
    }

    #[Test]
    public function failing_qa_requires_changes_and_edit_makes_report_stale(): void
    {
        $this->fakeAi([
            'qa.evaluate' => self::evaluation(70, [self::issue()], passed: false),
            'article.rebuild' => self::aiOk(['sections' => [], 'sections_count' => 0, 'facts_used_count' => 0, 'source_count' => 0, 'word_count' => 1]),
            'seo.preview' => self::aiOk(['seo_preview' => [], 'seo_origin' => 'article']),
        ]);
        $candidate = $this->makeCandidate();
        $article = $this->makeArticle($candidate);
        $this->postJson("/api/articles/{$article->id}/qa");

        $this->getJson("/api/articles/{$article->id}")->assertJsonPath('status', 'needs_changes')->assertJsonPath('qa_passed', false);
        $this->getJson("/api/articles/{$article->id}/qa")->assertJsonPath('issues.0.type', 'unsupported_claim')->assertJsonPath('issues.0.auto_fixable', true);
        $this->postJson("/api/article-versions/{$article->id}/approve")->assertStatus(409);

        $article->update(['title' => 'Zmieniony ręcznie bez nowej wersji']);
        $this->getJson("/api/articles/{$article->id}/qa")->assertJsonPath('is_stale', true)->assertJsonPath('qa_passed', false);
        $this->getJson("/api/articles/{$article->id}")->assertJsonPath('qa_status', 'stale')->assertJsonPath('qa_score', null);
    }

    #[Test]
    public function failed_job_marks_report_and_can_be_retried(): void
    {
        $this->fakeAi(['qa.evaluate' => self::aiError('invalid_output')]);
        $article = $this->makeArticle($this->makeCandidate());
        $this->postJson("/api/articles/{$article->id}/qa");
        $this->assertSame('failed', ArticleQa::query()->value('status'));

        $this->fakeAi(['qa.evaluate' => self::evaluation()]);
        $retry = $this->postJson("/api/articles/{$article->id}/qa/retry")->assertStatus(202)->json('id');
        $this->getJson("/api/jobs/{$retry}")->assertJsonPath('status', 'succeeded');
        $this->assertSame(2, ArticleQa::query()->count());
        $this->getJson("/api/articles/{$article->id}/qa")->assertJsonPath('status', 'completed');
    }

    #[Test]
    public function qa_requires_research_snapshot(): void
    {
        $article = $this->makeArticle($this->makeCandidate(), ['research_snapshot' => ['facts' => [], 'sources' => []]]);

        $this->postJson("/api/articles/{$article->id}/qa")->assertStatus(409)
            ->assertExactJson(['detail' => 'Ta wersja artykułu nie ma kompletnego snapshotu researchu.']);
    }
}
