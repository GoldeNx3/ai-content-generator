<?php

namespace Tests\Feature\Sources;

use Modules\Candidates\Models\Candidate;
use Modules\Sources\Console\SeedSourcesCommand;
use Modules\Sources\Models\Source;
use PHPUnit\Framework\Attributes\Test;
use Tests\TestCase;

final class SeedSourcesTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    private function defaultCount(): int
    {
        return array_sum(array_map(fn (string $group) => count(SeedSourcesCommand::GROUPS[$group]), SeedSourcesCommand::DEFAULT_GROUPS));
    }

    #[Test]
    public function single_workspace_is_used_without_options_and_reruns_skip_existing(): void
    {
        $this->artisan('sources:seed')->assertSuccessful();
        $this->artisan('sources:seed')->expectsOutputToContain('dodano 0 źródeł')->assertSuccessful();

        $this->assertSame($this->defaultCount(), Source::query()->where('workspace_id', $this->workspace->id)->count());
        $this->assertSame(0, Source::query()->where('url', 'like', '%marciniwuc%')->count());
    }

    #[Test]
    public function several_workspaces_require_an_explicit_choice(): void
    {
        $other = $this->otherWorkspace();

        $this->artisan('sources:seed')->expectsOutputToContain("Jest kilka workspace'ów")->assertFailed();
        $this->artisan('sources:seed', ['--workspace' => '999999'])->assertFailed();
        $this->assertSame(0, Source::query()->count());

        $this->artisan('sources:seed', ['--email' => mb_strtoupper($this->user->email)])->assertSuccessful();
        $this->artisan('sources:seed', ['--workspace' => (string) $other->id, '--group' => ['finance']])->assertSuccessful();

        $this->assertSame($this->defaultCount(), Source::query()->where('workspace_id', $this->workspace->id)->count());
        $this->assertSame(count(SeedSourcesCommand::GROUPS['finance']), Source::query()->where('workspace_id', $other->id)->count());
    }

    #[Test]
    public function groups_can_be_combined_and_unknown_groups_are_rejected(): void
    {
        $this->artisan('sources:seed', ['--group' => ['php,frontend']])->assertSuccessful();
        $this->assertSame(count(SeedSourcesCommand::GROUPS['php']) + count(SeedSourcesCommand::GROUPS['frontend']), Source::query()->count());

        $this->artisan('sources:seed', ['--group' => ['crypto']])->expectsOutputToContain('Nieznane grupy: crypto')->assertFailed();
    }

    #[Test]
    public function seeded_urls_are_unique(): void
    {
        $urls = array_merge(...array_map(fn (array $group) => array_column($group, 1), array_values(SeedSourcesCommand::GROUPS)));

        $this->assertSame(count($urls), count(array_unique($urls)));
    }

    #[Test]
    public function demo_seed_and_wordpress_import_use_the_same_workspace_choice(): void
    {
        $this->otherWorkspace();

        $this->artisan('demo:seed')->assertFailed();
        $this->artisan('demo:seed', ['--email' => $this->user->email])->assertSuccessful();
        $this->assertGreaterThan(0, Candidate::query()->where('workspace_id', $this->workspace->id)->count());

        config(['content.wordpress.import' => ['url' => 'https://wp.example/blog', 'api_url' => null, 'username' => 'editor', 'app_password' => 'secret']]);
        $this->artisan('wordpress:import-env')->expectsOutputToContain("Jest kilka workspace'ów")->assertFailed();
    }
}
