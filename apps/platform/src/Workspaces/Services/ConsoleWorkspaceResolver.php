<?php

namespace Modules\Workspaces\Services;

use Modules\Workspaces\Exceptions\WorkspaceNotResolvedException;
use Modules\Workspaces\Queries\WorkspaceDirectoryQuery;

final class ConsoleWorkspaceResolver
{
    public function __construct(private readonly WorkspaceDirectoryQuery $directory) {}

    public function resolve(?string $workspace, ?string $email): int
    {
        if (filled($workspace) && filled($email)) {
            throw new WorkspaceNotResolvedException('Podaj WORKSPACE albo EMAIL, nie oba.');
        }
        if (filled($workspace)) {
            $id = filter_var($workspace, FILTER_VALIDATE_INT);
            if ($id === false || $this->directory->execute(workspaceId: $id) === []) {
                throw new WorkspaceNotResolvedException("Workspace {$workspace} nie istnieje.\n".$this->listing());
            }

            return $id;
        }
        if (filled($email)) {
            $matches = $this->directory->execute(email: trim($email));
            if ($matches === []) {
                throw new WorkspaceNotResolvedException("Konto {$email} nie należy do żadnego workspace'u.\n".$this->listing());
            }
            if (count($matches) > 1) {
                throw new WorkspaceNotResolvedException("Konto {$email} należy do kilku workspace'ów, podaj WORKSPACE=<id>.\n".$this->listing($matches));
            }

            return $matches[0]['id'];
        }
        $all = $this->directory->execute();
        if ($all === []) {
            throw new WorkspaceNotResolvedException('Brak workspace\'u: najpierw załóż konto (make create-user EMAIL=...).');
        }
        if (count($all) > 1) {
            throw new WorkspaceNotResolvedException("Jest kilka workspace'ów, wskaż jeden: EMAIL=<konto> albo WORKSPACE=<id>.\n".$this->listing($all));
        }

        return $all[0]['id'];
    }

    private function listing(?array $workspaces = null): string
    {
        $lines = array_map(
            fn (array $workspace) => sprintf('  %d  %s  (%s)', $workspace['id'], $workspace['name'], implode(', ', $workspace['emails']) ?: 'bez członków'),
            $workspaces ?? $this->directory->execute(),
        );

        return "Workspace'y:\n".implode("\n", $lines);
    }
}
