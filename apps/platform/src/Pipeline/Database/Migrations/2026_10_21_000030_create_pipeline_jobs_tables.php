<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pipeline_jobs', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignId('workspace_id')->constrained()->restrictOnDelete();
            $table->unsignedBigInteger('candidate_id');
            $table->unsignedBigInteger('article_id')->nullable();
            $table->string('kind', 20);
            $table->string('status', 20)->default('queued');
            $table->jsonb('payload');
            $table->uuid('idempotency_key')->unique();
            $table->string('request_hash', 64);
            $table->string('stage', 50)->nullable();
            $table->integer('attempt_count')->default(0);
            $table->integer('max_attempts')->default(3);
            $table->timestampTz('available_at')->useCurrent();
            $table->timestampTz('started_at')->nullable();
            $table->timestampTz('finished_at')->nullable();
            $table->timestampTz('lease_expires_at')->nullable();
            $table->string('result_type', 30)->nullable();
            $table->unsignedBigInteger('result_id')->nullable();
            $table->string('error_code', 60)->nullable();
            $table->text('error_message')->nullable();
            $table->uuid('retry_of_job_id')->nullable();
            $table->jsonb('checkpoints')->default('{}');
            $table->timestampTz('created_at')->useCurrent();
            $table->timestampTz('updated_at')->useCurrent();
            $table->foreign(['candidate_id', 'workspace_id'])->references(['id', 'workspace_id'])->on('candidates')->restrictOnDelete();
            $table->index(['candidate_id', 'created_at']);
            $table->index(['workspace_id', 'created_at']);
        });
        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->foreign('retry_of_job_id')->references('id')->on('pipeline_jobs');
        });
        DB::statement("ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_kind CHECK (kind IN ('classify','research','write','qa_article','auto_fix_article','prepare_wordpress','publish_wordpress'))");
        DB::statement("ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_status CHECK (status IN ('queued','running','retrying','succeeded','failed'))");
        DB::statement("CREATE UNIQUE INDEX uq_pipeline_jobs_active_candidate ON pipeline_jobs (candidate_id) WHERE status IN ('queued','running','retrying')");

        Schema::create('pipeline_job_attempts', function (Blueprint $table) {
            $table->id();
            $table->foreignUuid('pipeline_job_id')->constrained('pipeline_jobs')->cascadeOnDelete();
            $table->integer('number');
            $table->timestampTz('started_at')->useCurrent()->index();
            $table->timestampTz('finished_at')->nullable();
            $table->string('outcome', 30)->default('running');
            $table->string('error_code', 60)->nullable();
            $table->text('error_message')->nullable();
            $table->string('last_stage', 50)->nullable();
            $table->jsonb('llm_calls')->default('[]');
            $table->unique(['pipeline_job_id', 'number']);
        });

        Schema::create('pipeline_job_batches', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
            $table->string('request_hash', 64);
            $table->jsonb('candidate_ids');
            $table->jsonb('skipped_ids')->default('[]');
            $table->timestampTz('created_at')->useCurrent();
        });

        Schema::table('candidates', function (Blueprint $table) {
            $table->foreign('classification_job_id')->references('id')->on('pipeline_jobs')->nullOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('candidates', fn (Blueprint $table) => $table->dropForeign(['classification_job_id']));
        Schema::dropIfExists('pipeline_job_batches');
        Schema::dropIfExists('pipeline_job_attempts');
        Schema::dropIfExists('pipeline_jobs');
    }
};
