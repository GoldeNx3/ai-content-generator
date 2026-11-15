<?php

namespace Modules\Shared\Routing;

use Closure;
use Illuminate\Contracts\Container\Container;
use Illuminate\Routing\Router;
use Modules\Articles\Queries\FindWorkspaceArticleQuery;
use Modules\AutoFix\Queries\FindWorkspaceFixQuery;
use Modules\Candidates\Queries\FindWorkspaceCandidateQuery;
use Modules\Pipeline\Queries\FindWorkspaceJobQuery;
use Modules\Shared\Exceptions\ApiException;
use Modules\Sources\Queries\FindWorkspaceSourceQuery;
use Modules\Workspaces\Queries\FindWorkspaceSuggestionQuery;
use Modules\Workspaces\Services\CurrentWorkspace;

final class WorkspaceBindings
{
    public const PARAMETERS = ['source', 'candidate', 'article', 'version', 'fix', 'job', 'suggestion'];

    public function __construct(private readonly Container $container) {}

    public function register(Router $router): void
    {
        $router->bind('source', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceSourceQuery::class)->execute($id, $ws)));
        $router->bind('candidate', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceCandidateQuery::class)->execute($id, $ws)));
        $router->bind('article', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceArticleQuery::class)->execute($id, $ws)));
        $router->bind('version', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceArticleQuery::class)->execute($id, $ws)));
        $router->bind('fix', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceFixQuery::class)->execute($id, $ws)));
        $router->bind('suggestion', $this->numeric(fn (int $id, int $ws) => $this->container->make(FindWorkspaceSuggestionQuery::class)->execute($id, $ws)));
        $router->bind('job', fn (string $value) => $this->container->make(FindWorkspaceJobQuery::class)
            ->execute($value, $this->workspaceId()) ?? throw new ApiException('not_found', 404));
    }

    private function numeric(Closure $resolve): Closure
    {
        return function (string $value) use ($resolve) {
            if (! ctype_digit($value)) {
                throw new ApiException('not_found', 404);
            }

            return $resolve((int) $value, $this->workspaceId()) ?? throw new ApiException('not_found', 404);
        };
    }

    private function workspaceId(): int
    {
        return $this->container->make(CurrentWorkspace::class)->id();
    }
}
