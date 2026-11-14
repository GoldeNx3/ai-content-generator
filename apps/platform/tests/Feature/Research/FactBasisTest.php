<?php

namespace Tests\Feature\Research;

use Illuminate\Support\Facades\DB;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class FactBasisTest extends TestCase
{
    use BuildsDomain, FakesAi;

    #[Test]
    public function the_basis_of_each_fact_is_kept_and_passed_to_the_writer(): void
    {
        $this->signIn();
        $candidate = $this->makeCandidate(['title' => 'Turbo X', 'external_url' => 'https://acme.example/turbo-x']);
        $this->fakeAi([
            'research.extract' => fn (array $r) => self::aiOk(['sources' => array_map(fn (string $url) => ['url' => $url, 'source_type' => 'official',
                'source_score' => 90, 'fetch_status' => 'success', 'http_status' => 200, 'error' => null, 'title' => 'T', 'publisher' => 'Acme',
                'published_at' => null, 'extracted_content' => 'Treść', 'raw_content' => '<p>x</p>'], $r['input']['urls'])]),
            'research.discover' => self::aiOk(['queries' => [], 'sources' => []]),
            'research.analyse' => fn (array $r) => self::aiOk(['summary' => 's', 'why_it_matters' => 'w', 'suggested_angle' => 'a', 'uncertainties' => [],
                'conflicts' => [], 'source_updates' => [], 'facts' => [
                    ['claim' => 'Turbo X jest 3x szybszy', 'importance' => 'high', 'confidence' => 60, 'basis' => 'vendor_claim', 'source_ids' => [$r['input']['sources'][0]['id']]],
                    ['claim' => 'Turbo X kosztuje 999 zł', 'importance' => 'medium', 'confidence' => 90, 'source_ids' => []],
                ]]),
            'article.brief' => self::aiError('invalid_output'),
        ]);

        $this->postJson("/api/candidates/{$candidate->id}/research")->assertStatus(202);
        $this->assertSame(['vendor_claim', null], DB::table('research_facts')->orderBy('id')->pluck('basis')->all());
        $this->getJson("/api/candidates/{$candidate->id}/research")->assertJsonPath('facts.0.basis', 'vendor_claim');

        $this->postJson("/api/candidates/{$candidate->id}/article", ['article_format' => 'auto'])->assertStatus(202);

        $facts = collect($this->aiRequests)->firstWhere('task', 'article.brief')['input']['research']['facts'];
        $this->assertSame('vendor_claim', $facts[0]['basis']);
        $this->assertNull($facts[1]['basis']);
    }
}
