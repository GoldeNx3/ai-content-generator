<?php

namespace Tests\Feature\Architecture;

use Illuminate\Routing\Route;
use Illuminate\Support\Str;
use Modules\AutoFix\Models\ArticleFix;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Shared\Routing\WorkspaceBindings;
use PHPUnit\Framework\Attributes\Test;
use ReflectionClass;
use ReflectionMethod;
use Tests\Support\BuildsArticles;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class ArchitectureTest extends TestCase
{
    use BuildsArticles, BuildsDomain;

    private const PUBLIC_CONTROLLERS = ['RegisterController', 'LoginController', 'LogoutController'];

    private function apiRoutes(): array
    {
        return array_values(array_filter(app('router')->getRoutes()->getRoutes(), fn (Route $route) => str_starts_with($route->uri(), 'api/')));
    }

    private function controllers(): array
    {
        return array_map(fn (string $path) => 'Modules\\'.str_replace(['/', '.php'], ['\\', ''], Str::after($path, base_path('src/'))),
            glob(base_path('src/*/Http/Controllers/*Controller.php')));
    }

    #[Test]
    public function controllers_are_final_invokable_and_protected(): void
    {
        foreach ($this->controllers() as $class) {
            $reflection = new ReflectionClass($class);
            $this->assertTrue($reflection->isFinal(), "{$class} must be final");
            $public = array_filter($reflection->getMethods(ReflectionMethod::IS_PUBLIC), fn ($m) => $m->class === $class && $m->name !== '__construct');
            $this->assertSame(['__invoke'], array_values(array_map(fn ($m) => $m->name, $public)), "{$class} must be invokable only");
            if (! in_array($reflection->getShortName(), self::PUBLIC_CONTROLLERS, true)) {
                $middleware = array_merge(...array_map(fn ($a) => (array) $a->getArguments()[0], $reflection->getAttributes(\Spatie\RouteAttributes\Attributes\Middleware::class)));
                $this->assertContains('auth:sanctum', $middleware, "{$class} must require auth:sanctum");
            }
        }
    }

    #[Test]
    public function every_route_parameter_is_workspace_bound(): void
    {
        $routes = $this->apiRoutes();
        $this->assertGreaterThan(50, count($routes));
        foreach ($routes as $route) {
            foreach ($route->parameterNames() as $name) {
                $this->assertContains($name, WorkspaceBindings::PARAMETERS, "Route {$route->uri()} uses unbound parameter {$name}");
            }
        }
    }

    #[Test]
    public function queries_and_commands_have_single_execute_method(): void
    {
        $paths = [...glob(base_path('src/*/Queries/*.php')), ...glob(base_path('src/*/Commands/*.php'))];
        $this->assertNotEmpty($paths);
        foreach ($paths as $path) {
            $class = 'Modules\\'.str_replace(['/', '.php'], ['\\', ''], Str::after($path, base_path('src/')));
            $reflection = new ReflectionClass($class);
            $public = array_values(array_map(fn ($m) => $m->name, array_filter(
                $reflection->getMethods(ReflectionMethod::IS_PUBLIC),
                fn ($m) => $m->class === $class && $m->name !== '__construct' && ! $m->isStatic(),
            )));
            $this->assertSame(['execute'], $public, "{$class} must expose only execute()");
        }
    }

    #[Test]
    public function foreign_resources_are_not_found_on_every_route(): void
    {
        $this->signIn();
        $foreignWorkspace = $this->otherWorkspace();
        $candidate = $this->makeCandidate([], $foreignWorkspace->id);
        $article = $this->makeArticle($candidate);
        $qa = \Modules\Qa\Models\ArticleQa::query()->create(['article_id' => $article->id, 'article_version' => 1, 'input_hash' => 'x', 'input_snapshot' => []]);
        $fix = ArticleFix::query()->create(['source_article_version_id' => $article->id, 'qa_id' => $qa->id, 'iteration' => 1, 'input_hash' => 'x', 'input_snapshot' => []]);
        $job = PipelineJob::query()->create(['workspace_id' => $foreignWorkspace->id, 'candidate_id' => $candidate->id, 'kind' => 'classify',
            'status' => 'failed', 'payload' => [], 'idempotency_key' => (string) Str::uuid(), 'request_hash' => 'x']);
        $ids = ['source' => $candidate->source_id, 'candidate' => $candidate->id, 'article' => $article->id, 'version' => $article->id,
            'fix' => $fix->id, 'job' => $job->id];

        $checked = 0;
        foreach ($this->apiRoutes() as $route) {
            if ($route->parameterNames() === []) {
                continue;
            }
            $uri = preg_replace_callback('/\{(\w+)\}/', fn ($m) => $ids[$m[1]], $route->uri());
            foreach (array_diff($route->methods(), ['HEAD']) as $method) {
                $this->json($method, '/'.$uri, [])->assertNotFound()->assertExactJson(['detail' => ['code' => 'not_found']]);
                $checked++;
            }
        }
        $this->assertGreaterThan(30, $checked);
    }
}
