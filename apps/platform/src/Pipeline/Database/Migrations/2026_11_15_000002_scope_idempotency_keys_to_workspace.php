<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->dropUnique(['idempotency_key']);
            $table->unique(['workspace_id', 'idempotency_key']);
        });
    }

    public function down(): void
    {
        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->dropUnique(['workspace_id', 'idempotency_key']);
            $table->unique(['idempotency_key']);
        });
    }
};
