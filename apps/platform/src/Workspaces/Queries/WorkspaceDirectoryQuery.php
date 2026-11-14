<?php

namespace Modules\Workspaces\Queries;

use Illuminate\Support\Facades\DB;

final class WorkspaceDirectoryQuery
{
    public function execute(?int $workspaceId = null, ?string $email = null): array
    {
        $rows = DB::table('workspaces')
            ->leftJoin('workspace_members', 'workspace_members.workspace_id', '=', 'workspaces.id')
            ->leftJoin('users', 'users.id', '=', 'workspace_members.user_id')
            ->when($workspaceId !== null, fn ($query) => $query->where('workspaces.id', $workspaceId))
            ->when($email !== null, fn ($query) => $query->whereIn('workspaces.id', DB::table('workspace_members')
                ->join('users', 'users.id', '=', 'workspace_members.user_id')
                ->whereRaw('lower(users.email) = ?', [mb_strtolower($email)])
                ->select('workspace_members.workspace_id')))
            ->orderBy('workspaces.id')
            ->orderBy('users.email')
            ->get(['workspaces.id', 'workspaces.name', 'users.email']);

        $directory = [];
        foreach ($rows as $row) {
            $directory[$row->id] ??= ['id' => (int) $row->id, 'name' => (string) $row->name, 'emails' => []];
            if ($row->email !== null) {
                $directory[$row->id]['emails'][] = (string) $row->email;
            }
        }

        return array_values($directory);
    }
}
