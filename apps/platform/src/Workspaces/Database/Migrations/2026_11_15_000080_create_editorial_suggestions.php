<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    private const KINDS = "'classify','research','write','qa_article','auto_fix_article','prepare_wordpress','publish_wordpress'";

    public function up(): void
    {
        Schema::create('editorial_suggestions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
            $table->foreignId('candidate_id')->constrained()->cascadeOnDelete();
            $table->foreignUuid('job_id')->nullable()->constrained('pipeline_jobs')->nullOnDelete();
            $table->string('kind', 20);
            $table->string('text', 200);
            $table->string('why', 300);
            $table->string('status', 20)->default('pending');
            $table->timestampsTz();
            $table->index(['candidate_id', 'id']);
        });
        DB::statement("ALTER TABLE editorial_suggestions ADD CONSTRAINT ck_editorial_suggestions_kind CHECK (kind IN ('style_rule','banned_phrase'))");
        DB::statement("ALTER TABLE editorial_suggestions ADD CONSTRAINT ck_editorial_suggestions_status CHECK (status IN ('pending','accepted','dismissed'))");
        DB::statement('ALTER TABLE pipeline_jobs DROP CONSTRAINT ck_pipeline_jobs_kind');
        DB::statement('ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_kind CHECK (kind IN ('.self::KINDS.",'learn_feedback'))");
    }

    public function down(): void
    {
        DB::statement("DELETE FROM pipeline_jobs WHERE kind = 'learn_feedback'");
        DB::statement('ALTER TABLE pipeline_jobs DROP CONSTRAINT ck_pipeline_jobs_kind');
        DB::statement('ALTER TABLE pipeline_jobs ADD CONSTRAINT ck_pipeline_jobs_kind CHECK (kind IN ('.self::KINDS.'))');
        Schema::dropIfExists('editorial_suggestions');
    }
};
