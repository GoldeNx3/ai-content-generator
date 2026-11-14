<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->timestamp('cancel_requested_at')->nullable();
            $table->foreignId('cancelled_by')->nullable()->constrained('users')->nullOnDelete();
        });
        DB::statement('ALTER TABLE pipeline_jobs DROP CONSTRAINT ck_pipeline_jobs_status');
        DB::statement("ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_status CHECK (status IN ('queued','running','retrying','succeeded','failed','cancelled'))");
    }

    public function down(): void
    {
        DB::statement("UPDATE pipeline_jobs SET status = 'failed' WHERE status = 'cancelled'");
        DB::statement('ALTER TABLE pipeline_jobs DROP CONSTRAINT ck_pipeline_jobs_status');
        DB::statement("ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_status CHECK (status IN ('queued','running','retrying','succeeded','failed'))");
        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->dropConstrainedForeignId('cancelled_by');
            $table->dropColumn('cancel_requested_at');
        });
    }
};
