<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        $sharedWorkspaces = DB::table('workspace_members')->groupBy('workspace_id')->havingRaw('COUNT(*) > 1')->pluck('workspace_id')->all();
        $multiWorkspaceUsers = DB::table('workspace_members')->groupBy('user_id')->havingRaw('COUNT(*) > 1')->pluck('user_id')->all();
        if ($sharedWorkspaces !== [] || $multiWorkspaceUsers !== []) {
            throw new RuntimeException(sprintf(
                'One account = one workspace: resolve shared workspaces [%s] and users in several workspaces [%s] before migrating.',
                implode(', ', $sharedWorkspaces), implode(', ', $multiWorkspaceUsers),
            ));
        }
        DB::table('workspace_members')->where('role', '!=', 'owner')->update(['role' => 'owner']);
        DB::statement('CREATE UNIQUE INDEX uq_workspace_members_user ON workspace_members (user_id)');
        DB::statement('CREATE UNIQUE INDEX uq_workspace_members_workspace ON workspace_members (workspace_id)');
    }

    public function down(): void
    {
        DB::statement('DROP INDEX IF EXISTS uq_workspace_members_workspace');
        DB::statement('DROP INDEX IF EXISTS uq_workspace_members_user');
    }
};
