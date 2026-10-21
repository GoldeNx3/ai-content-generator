<?php

namespace Tests\Feature\AutoFix;

use Modules\Articles\Models\Article;
use Modules\AutoFix\Models\ArticleFix;
use PHPUnit\Framework\Attributes\Test;
use Tests\Feature\Qa\QaPipelineTest;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class AutoFixPipelineTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    private function fixResult(int $issueId, bool $changed = true): array
    {
        return self::aiOk([
            'summary' => 'Poprawiono', 'fix_results' => [['qa_issue_id' => $issueId, 'status' => $changed ? 'fixed' : 'skipped', 'reason' => 'ok']],
            'issues_fixed' => $changed ? 1 : 0, 'issues_skipped' => $changed ? 0 : 1, 'change_ratio' => 0.05,
            'changes' => $changed ? [['field' => 'content', 'before' => 'Treść.', 'after' => 'Nowa treść.']] : [], 'warnings' => [],
            'changed' => $changed,
            'article' => ['title' => 'Tytuł', 'slug' => 'tytul', 'lead' => 'Lead.', 'content' => $changed ? "## Sekcja\n\nNowa treść.\n" : "## Sekcja\n\nTreść.\n",
                'meta_title' => 'Meta', 'meta_description' => 'Opis'],
            'lead_fact_ids' => [], 'patches' => [],
        ], [self::llmCall('fixing_article', '0.001500', 'gpt-fix')]);
    }

    private function failedQaArticle(): Article
    {
        $this->fakeAi(['qa.evaluate' => QaPipelineTest::evaluation(70, [QaPipelineTest::issue(), QaPipelineTest::issue(['type' => 'contradiction', 'excerpt' => 'X'])], passed: false)]);
        $article = $this->makeArticle($this->makeCandidate());
        $this->postJson("/api/articles/{$article->id}/qa");

        return $article->refresh();
    }

    #[Test]
    public function auto_fix_creates_new_version_and_report(): void
    {
        $article = $this->failedQaArticle();
        $issues = $this->getJson("/api/articles/{$article->id}/qa")->json('issues');
        $this->fakeAi([
            'autofix.fix' => fn () => $this->fixResult($issues[0]['id']),
            'article.rebuild' => self::aiOk(['sections' => [], 'sections_count' => 1, 'facts_used_count' => 1, 'source_count' => 1, 'word_count' => 4]),
            'seo.preview' => self::aiOk(['seo_preview' => ['excerpt' => 'E'], 'seo_origin' => 'article']),
        ]);

        $job = $this->postJson("/api/article-versions/{$article->id}/auto-fix")->assertStatus(202)->json('id');
        $this->getJson("/api/jobs/{$job}")->assertJsonPath('status', 'succeeded')->assertJsonPath('result.type', 'article_fix');
        $payload = $this->aiRequests[0]['input']['payload'];
        $this->assertSame(1, $payload['iteration']);
        $this->assertSame([true, false], array_column($payload['issues'], 'auto_fixable'));

        $fix = ArticleFix::query()->firstOrFail();
        $child = Article::query()->where('created_by', 'auto_fix')->firstOrFail();
        $this->getJson("/api/article-fixes/{$fix->id}")->assertOk()->assertJsonPath('status', 'completed')
            ->assertJsonPath('result_article_version_id', $child->id)->assertJsonPath('issues_fixed', 1)
            ->assertJsonPath('estimated_cost_usd', '0.001500')->assertJsonPath('issues.0.status', 'fixed');
        $this->assertSame("## Sekcja\n\nNowa treść.\n", $child->generated_content);
        $this->assertSame(1, $child->auto_fix_iteration);
        $this->getJson("/api/article-versions/{$child->id}/fixes")->assertJsonCount(1);
        $this->getJson("/api/articles/{$child->id}")->assertJsonPath('auto_fix_iterations_remaining', 1)->assertJsonPath('qa_status', 'required');
    }

    #[Test]
    public function auto_fix_without_changes_requires_manual_review(): void
    {
        $article = $this->failedQaArticle();
        $issueId = $this->getJson("/api/articles/{$article->id}/qa")->json('issues.0.id');
        $this->fakeAi(['autofix.fix' => $this->fixResult($issueId, changed: false)]);

        $this->postJson("/api/article-versions/{$article->id}/auto-fix", ['issue_ids' => [$issueId]])->assertStatus(202);
        $this->assertSame('manual_review_required', $article->refresh()->status->value);
        $this->assertSame(1, Article::query()->count());
    }

    #[Test]
    public function auto_fix_guards(): void
    {
        $article = $this->makeArticle($this->makeCandidate());
        $this->postJson("/api/article-versions/{$article->id}/auto-fix")->assertStatus(409)
            ->assertExactJson(['detail' => 'Auto Fix wymaga aktualnego ukończonego QA.']);

        $failed = $this->failedQaArticle();
        $this->postJson("/api/article-versions/{$failed->id}/auto-fix", ['issue_ids' => [999999]])->assertStatus(422);
        $this->postJson("/api/article-versions/{$failed->id}/auto-fix", ['issue_ids' => 'x'])->assertStatus(422);

        $this->fakeAi(['autofix.fix' => self::aiError('invalid_output')]);
        $this->postJson("/api/article-versions/{$failed->id}/auto-fix");
        $fix = ArticleFix::query()->with('issues')->firstOrFail();
        $this->assertSame('failed', $fix->status);
        $this->assertSame(['failed', 'failed'], $fix->issues->pluck('status')->all());
    }
}
