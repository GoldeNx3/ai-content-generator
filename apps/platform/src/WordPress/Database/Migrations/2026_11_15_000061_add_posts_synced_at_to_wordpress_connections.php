<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('wordpress_connections', function (Blueprint $table) {
            $table->timestampTz('posts_synced_at')->nullable();
        });
        DB::statement('UPDATE wordpress_connections c SET posts_synced_at = (SELECT MAX(p.synced_at) FROM wordpress_posts p WHERE p.workspace_id = c.workspace_id)');
    }

    public function down(): void
    {
        Schema::table('wordpress_connections', function (Blueprint $table) {
            $table->dropColumn('posts_synced_at');
        });
    }
};
