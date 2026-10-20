<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('articles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('candidate_id')->constrained()->cascadeOnDelete();
            $table->foreignId('research_id')->nullable()->constrained('researches')->nullOnDelete();
            $table->foreignId('parent_version_id')->nullable()->constrained('articles')->restrictOnDelete();
            $table->foreignUuid('generation_job_id')->nullable()->unique()->constrained('pipeline_jobs')->nullOnDelete();
            $table->integer('version');
            $table->boolean('is_current')->default(true);
            $table->string('status', 30)->default('draft');
            $table->string('created_by', 30)->default('generated');
            $table->text('creation_reason')->nullable();
            $table->string('content_hash', 64)->default('');
            $table->integer('auto_fix_iteration')->default(0);
            $table->timestampTz('approved_at')->nullable();
            $table->string('approved_by', 100)->nullable();
            $table->text('rejection_reason')->nullable();
            $table->string('title', 300);
            $table->string('slug', 300);
            $table->text('lead');
            $table->text('content');
            $table->text('generated_content');
            $table->string('meta_title', 300);
            $table->string('meta_description', 500);
            $table->string('article_type', 20);
            $table->text('angle')->nullable();
            $table->boolean('qa_passed')->default(false);
            $table->boolean('is_edited')->default(false);
            $table->jsonb('seo_data')->default('{}');
            $table->jsonb('seo_preview')->default('{}');
            $table->string('seo_origin', 30)->default('article');
            $table->jsonb('brief');
            $table->jsonb('sections');
            $table->jsonb('lead_fact_ids')->default('[]');
            $table->jsonb('generation_options');
            $table->jsonb('research_snapshot');
            $table->jsonb('validation_warnings')->default('[]');
            $table->integer('word_count')->default(0);
            $table->integer('sections_count')->default(0);
            $table->integer('facts_used_count')->default(0);
            $table->integer('facts_available_count')->default(0);
            $table->integer('source_count')->default(0);
            $table->string('llm_model', 100)->nullable();
            $table->integer('llm_input_tokens')->default(0);
            $table->integer('llm_output_tokens')->default(0);
            $table->decimal('estimated_cost_usd', 12, 6)->nullable();
            $table->string('brief_llm_model', 100)->nullable();
            $table->integer('brief_input_tokens')->default(0);
            $table->integer('brief_output_tokens')->default(0);
            $table->decimal('brief_cost_usd', 12, 6)->nullable();
            $table->integer('writer_input_tokens')->default(0);
            $table->integer('writer_output_tokens')->default(0);
            $table->decimal('writer_cost_usd', 12, 6)->nullable();
            $table->timestampsTz();
            $table->index('candidate_id');
            $table->unique(['candidate_id', 'version']);
        });
        DB::statement("CREATE UNIQUE INDEX uq_articles_one_approved_per_candidate ON articles (candidate_id) WHERE status = 'approved'");
        DB::statement('CREATE UNIQUE INDEX uq_articles_one_current_per_candidate ON articles (candidate_id) WHERE is_current');

        Schema::table('pipeline_jobs', function (Blueprint $table) {
            $table->foreign('article_id')->references('id')->on('articles')->restrictOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('pipeline_jobs', fn (Blueprint $table) => $table->dropForeign(['article_id']));
        Schema::dropIfExists('articles');
    }
};
