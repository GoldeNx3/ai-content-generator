<?php

namespace Tests\Feature\Pipeline;

use Modules\Auth\Models\User;
use Modules\Candidates\Models\Candidate;
use Modules\Research\Models\Research;
use Modules\Sources\Models\Source;
use Modules\WordPress\Models\WordPressConnection;
use Modules\Workspaces\Models\Workspace;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class WipeDataTest extends TestCase
{
    use BuildsArticles, BuildsDomain;

    #[Test]
    public function wipe_clears_domain_data_and_keeps_accounts_and_connections(): void
    {
        $this->signIn();
        $this->completedResearch($this->makeCandidate());
        WordPressConnection::query()->create([
            'workspace_id' => $this->workspace->id, 'site_url' => 'https://wp.example', 'username' => 'u',
            'app_password' => 'p', 'instance_id' => 'ce-test',
        ]);

        $this->artisan('data:wipe', ['--force' => true])->assertSuccessful();

        $this->assertSame(0, Source::query()->count());
        $this->assertSame(0, Candidate::query()->count());
        $this->assertSame(0, Research::query()->count());
        $this->assertSame(1, User::query()->count());
        $this->assertSame(1, Workspace::query()->count());
        $this->assertSame(1, WordPressConnection::query()->count());
    }

    #[Test]
    public function wipe_asks_for_confirmation(): void
    {
        $this->signIn();
        $this->makeSource();

        $this->artisan('data:wipe')->expectsConfirmation('Usunąć źródła, kandydatów, artykuły i zadania?', 'no')->assertFailed();

        $this->assertSame(1, Source::query()->count());
    }
}
