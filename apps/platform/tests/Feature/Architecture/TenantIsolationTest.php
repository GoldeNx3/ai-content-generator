<?php

namespace Tests\Feature\Architecture;

use Illuminate\Routing\Route;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Modules\Auth\Models\User;
use Modules\Pipeline\Models\PipelineJobAttempt;
use Modules\Sources\Models\Source;
use Modules\Sources\Queries\ListSourcesQuery;
use Modules\Sources\Services\IngestionService;
use Modules\WordPress\Models\WordPressConnection;
use Modules\Workspaces\Models\Workspace;
use Modules\Workspaces\Models\WorkspaceMember;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\Support\FakesAi;
use Tests\TestCase;

final class TenantIsolationTest extends TestCase
{
    use BuildsArticles, BuildsDomain, FakesAi;

    private const MARKER = 'OBCY-TENANT-7f3a';

    private const PUBLIC_ROUTES = ['api/auth/login', 'api/auth/register', 'api/auth/logout'];

    private function otherAccount(): Workspace
    {
        $workspace = Workspace::query()->create(['name' => self::MARKER, 'paused_at' => now(), 'auto_fetch_enabled' => true]);
        $user = User::query()->create(['email' => 'obcy@example.com', 'password' => 'secret-password']);
        WorkspaceMember::query()->create(['workspace_id' => $workspace->id, 'user_id' => $user->id, 'role' => 'owner']);

        return $workspace;
    }

    private function seedForeignData(Workspace $other): string
    {
        Source::query()->create(['workspace_id' => $other->id, 'name' => self::MARKER, 'url' => 'https://obcy.example.com/feed.xml']);
        $candidate = $this->makeCandidate(['title' => self::MARKER, 'total_score' => 99], $other->id);
        $job = $this->makeJob(['status' => 'running', 'attempt_count' => 1], $candidate);
        $queued = $this->makeJob([], $this->makeCandidate(['title' => self::MARKER.' 2'], $other->id));
        $this->makeArticle($candidate, ['title' => self::MARKER]);
        (new WordPressConnection)->forceFill([
            'workspace_id' => $other->id, 'site_url' => 'https://'.strtolower(self::MARKER).'.example.com', 'username' => self::MARKER,
            'app_password' => 'secret', 'instance_id' => (string) Str::uuid(), 'wp_user_name' => self::MARKER,
        ])->save();
        PipelineJobAttempt::query()->create([
            'pipeline_job_id' => $job->id, 'number' => 1, 'started_at' => now(), 'llm_calls' => [self::llmCall('classifying', '7.000000')],
        ]);

        return $job->id;
    }

    private function parameterlessGetRoutes(): array
    {
        return array_values(array_filter(
            app('router')->getRoutes()->getRoutes(),
            fn (Route $route) => str_starts_with($route->uri(), 'api/') && in_array('GET', $route->methods(), true)
                && $route->parameterNames() === [] && ! in_array($route->uri(), self::PUBLIC_ROUTES, true),
        ));
    }

    #[Test]
    public function no_list_or_aggregate_route_exposes_another_account(): void
    {
        $this->signIn();
        $this->makeCandidate(['title' => 'Mój temat']);
        $foreignJobId = $this->seedForeignData($this->otherAccount());

        $routes = $this->parameterlessGetRoutes();
        $this->assertGreaterThan(5, count($routes));
        foreach ($routes as $route) {
            $response = $this->getJson('/'.$route->uri());
            $this->assertLessThan(500, $response->status(), "GET {$route->uri()} failed");
            $body = $response->getContent();
            $this->assertStringNotContainsString(self::MARKER, $body, "GET {$route->uri()} leaks another account's data");
            $this->assertStringNotContainsString($foreignJobId, $body, "GET {$route->uri()} leaks another account's job");
        }
    }

    #[Test]
    public function counters_and_settings_reflect_only_the_own_account(): void
    {
        $this->signIn();
        $this->seedForeignData($this->otherAccount());

        $this->getJson('/api/jobs/stats')->assertJsonPath('total', 0)->assertJsonPath('running', 0);
        $this->getJson('/api/jobs?status=all')->assertJsonPath('total', 0);
        $this->getJson('/api/candidates')->assertJsonPath('total', 0);
        $this->getJson('/api/stats')->assertJsonPath('candidates_today', 0)->assertJsonPath('average_score', null);
        $this->assertSame(0.0, (float) $this->getJson('/api/usage')->json('spent_usd'));
        $this->getJson('/api/workspace/automation')->assertJsonPath('paused_at', null)->assertJsonPath('auto_fetch_enabled', false);
    }

    #[Test]
    public function source_queries_cannot_span_all_workspaces(): void
    {
        $this->assertThrows(fn () => app(IngestionService::class)->fetchAllActive(null), \TypeError::class);
        $this->assertThrows(fn () => app(ListSourcesQuery::class)->execute(null), \TypeError::class);
    }

    private function foreignState(int $workspaceId): array
    {
        return [
            'workspace' => (array) DB::table('workspaces')->where('id', $workspaceId)->first(),
            'connection' => (array) DB::table('wordpress_connections')->where('workspace_id', $workspaceId)->first(),
            'sources' => DB::table('sources')->where('workspace_id', $workspaceId)->orderBy('id')->get()->map(fn ($row) => (array) $row)->all(),
            'candidates' => DB::table('candidates')->where('workspace_id', $workspaceId)->count(),
            'jobs' => DB::table('pipeline_jobs')->where('workspace_id', $workspaceId)->orderBy('id')->get(['id', 'status', 'cancel_requested_at'])->map(fn ($row) => (array) $row)->all(),
        ];
    }

    #[Test]
    public function no_parameterless_write_route_changes_another_account(): void
    {
        Http::fake(['*' => Http::response('', 500)]);
        $this->fakeAi(['classify' => self::aiOk(['relevance' => 1, 'freshness' => 1, 'search_potential' => 1, 'commercial_potential' => 1, 'total_score' => 1, 'category' => 'news', 'reason' => 'r'])]);
        $this->signIn();
        $this->makeCandidate(['title' => 'Mój temat']);
        $other = $this->otherAccount();
        $this->seedForeignData($other);
        $before = $this->foreignState($other->id);

        $routes = array_values(array_filter(
            app('router')->getRoutes()->getRoutes(),
            fn (Route $route) => str_starts_with($route->uri(), 'api/') && $route->parameterNames() === []
                && array_intersect(['POST', 'PATCH', 'DELETE'], $route->methods()) !== [] && ! in_array($route->uri(), self::PUBLIC_ROUTES, true),
        ));
        $this->assertGreaterThan(10, count($routes));
        foreach ($routes as $route) {
            foreach (array_intersect(['POST', 'PATCH', 'DELETE'], $route->methods()) as $method) {
                $response = $this->json($method, '/'.$route->uri(), ['auto_fetch_enabled' => false, 'limit' => 5]);
                $this->assertLessThan(500, $response->status(), "{$method} {$route->uri()} failed");
                $this->assertSame($before, $this->foreignState($other->id), "{$method} {$route->uri()} changed another account");
            }
        }
    }
}
