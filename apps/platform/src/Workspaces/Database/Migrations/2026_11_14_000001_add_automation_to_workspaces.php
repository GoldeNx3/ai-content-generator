<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            $table->boolean('auto_fetch_enabled')->default(false);
            $table->unsignedSmallInteger('auto_fetch_interval_minutes')->default(60);
            $table->boolean('auto_classify_enabled')->default(false);
            $table->unsignedSmallInteger('auto_classify_batch_limit')->default(20);
            $table->timestamp('last_auto_run_at')->nullable();
            $table->jsonb('last_auto_run_result')->nullable();
            $table->timestamp('paused_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('workspaces', function (Blueprint $table) {
            $table->dropColumn([
                'auto_fetch_enabled', 'auto_fetch_interval_minutes', 'auto_classify_enabled', 'auto_classify_batch_limit',
                'last_auto_run_at', 'last_auto_run_result', 'paused_at',
            ]);
        });
    }
};
