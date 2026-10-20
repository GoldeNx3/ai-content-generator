<?php

namespace Tests\Feature\Articles;

use Modules\Articles\Models\Article;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class ArticlesTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    private function writerFakes(): array
    {
        return [
            'article.brief' => self::aiOk(['context' => ['candidate_title' => 'T'], 'brief' => ['article_format' => 'news'], 'warnings' => ['W1']],
                [self::llmCall('building_brief', '0.000500', 'gpt-brief')]),
            'article.write' => fn () => self::aiOk(self::writtenArticle(), [self::llmCall('writing', '0.004000', 'gpt-writer')]),
            'article.rebuild' => fn (array $request) => self::aiOk(['sections' => [], 'sections_count' => 0, 'facts_used_count' => 0, 'source_count' => 0,
                'word_count' => str_word_count($request['input']['content'])]),
            'seo.preview' => self::aiOk(['seo_preview' => ['excerpt' => 'nowy'], 'seo_origin' => 'article']),
        ];
    }

    #[Test]
    public function generation_requires_completed_research(): void
    {
        $candidate = $this->makeCandidate();
        $this->postJson("/api/candidates/{$candidate->id}/article", ['length' => 'auto'])->assertStatus(409)
            ->assertExactJson(['detail' => 'Complete research before generating an article.']);
        $this->postJson("/api/candidates/{$candidate->id}/article", ['length' => 'huge'])->assertStatus(422);
    }

    #[Test]
    public function generation_creates_version_with_costs_and_regeneration_links_parent(): void
    {
        $this->fakeAi($this->writerFakes());
        $candidate = $this->makeCandidate(['category' => 'guide']);
        $this->completedResearch($candidate);

        $jobId = $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto', 'length' => 'long'])->json('id');
        $this->getJson("/api/jobs/{$jobId}")->assertJsonPath('status', 'succeeded')->assertJsonPath('result.type', 'article');
        $this->assertSame('guide', $this->aiRequests[0]['input']['article_type']);
        $this->assertSame('long', $this->aiRequests[0]['input']['request']['length']);
        $this->assertSame(['W1'], $this->aiRequests[1]['input']['warnings']);

        $article = Article::query()->firstOrFail();
        $this->getJson("/api/articles/{$article->id}")->assertOk()
            ->assertJsonPath('version', 1)->assertJsonPath('created_by', 'generated')->assertJsonPath('qa_status', 'required')
            ->assertJsonPath('brief_cost_usd', '0.000500')->assertJsonPath('writer_cost_usd', '0.004000')
            ->assertJsonPath('estimated_cost_usd', '0.004500')->assertJsonPath('llm_model', 'gpt-writer')
            ->assertJsonPath('article_format', 'news')->assertJsonPath('auto_fix_iterations_remaining', 2);
        $this->assertSame(64, strlen($article->content_hash));

        $this->postJson("/api/articles/{$article->id}/regenerate", ['angle' => 'Nowy kąt'])->assertStatus(202);
        $versions = $this->getJson("/api/candidates/{$candidate->id}/articles")->assertJsonCount(2)->json();
        $this->assertSame([2, 1], array_column($versions, 'version'));
        $this->assertSame('regenerated', $versions[0]['created_by']);
        $this->assertSame($article->id, $versions[0]['parent_version_id']);
        $this->assertSame([true, false], array_column($versions, 'is_current'));
        $this->assertSame('Nowy kąt', end($this->aiRequests)['input']['request']['angle']);
    }

    #[Test]
    public function manual_edit_creates_child_version_and_unchanged_edit_is_noop(): void
    {
        $this->fakeAi($this->writerFakes());
        $candidate = $this->makeCandidate();
        $article = $this->makeArticle($candidate);

        $this->patchJson("/api/articles/{$article->id}", ['title' => 'Tytuł'])->assertOk()->assertJsonPath('id', $article->id);
        $this->assertSame([], $this->aiRequests);

        $child = $this->patchJson("/api/articles/{$article->id}", ['content' => "## Nowa\n\nInna treść tekstu.\n", 'title' => ' Nowy '])
            ->assertOk()->assertJsonPath('version', 2)->assertJsonPath('created_by', 'manual_edit')
            ->assertJsonPath('is_edited', true)->assertJsonPath('title', 'Nowy')->assertJsonPath('estimated_cost_usd', '0.000000')
            ->assertJsonPath('seo_preview.excerpt', 'nowy')->assertJsonPath('parent_version_id', $article->id)->json();
        $this->assertNotSame($article->content_hash, $child['content_hash']);
        $this->assertSame(['article.rebuild', 'seo.preview'], array_column($this->aiRequests, 'task'));
        $this->assertFalse($article->refresh()->is_current);
        $this->patchJson("/api/articles/{$article->id}", ['title' => ''])->assertStatus(422);
    }

    #[Test]
    public function status_changes_are_guarded(): void
    {
        $candidate = $this->makeCandidate();
        $article = $this->makeArticle($candidate);

        $this->patchJson("/api/articles/{$article->id}/status", ['status' => 'review'])->assertStatus(409);
        $this->patchJson("/api/articles/{$article->id}/status", ['status' => 'approved'])->assertStatus(409)
            ->assertExactJson(['detail' => 'Zatwierdzenie wymaga aktualnego, zaliczonego QA i statusu ready_for_approval.']);
        $this->postJson("/api/article-versions/{$article->id}/reject", ['reason' => 'Słabe'])->assertOk()
            ->assertJsonPath('status', 'rejected')->assertJsonPath('rejection_reason', 'Słabe');
        $foreign = $this->makeArticle($this->makeCandidate([], $this->otherWorkspace()->id));
        $this->getJson("/api/articles/{$foreign->id}")->assertNotFound();
        $this->postJson("/api/article-versions/{$foreign->id}/approve")->assertNotFound();
    }
}
