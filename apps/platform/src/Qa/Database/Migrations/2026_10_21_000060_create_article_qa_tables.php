<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('article_qas', function (Blueprint $table) {
            $table->id();
            $table->foreignId('article_id')->constrained()->cascadeOnDelete();
            $table->integer('article_version');
            $table->foreignUuid('job_id')->nullable()->unique()->constrained('pipeline_jobs')->nullOnDelete();
            $table->string('status', 20)->default('pending');
            $table->string('input_hash', 64);
            $table->jsonb('input_snapshot');
            $table->jsonb('claims')->default('[]');
            $table->integer('overall_score')->nullable();
            $table->integer('factual_score')->nullable();
            $table->integer('source_score')->nullable();
            $table->integer('style_score')->nullable();
            $table->integer('structure_score')->nullable();
            $table->integer('seo_score')->nullable();
            $table->integer('supported_claims_count')->default(0);
            $table->integer('unsupported_claims_count')->default(0);
            $table->integer('critical_issue_count')->default(0);
            $table->integer('warning_count')->default(0);
            $table->text('summary')->nullable();
            $table->string('llm_model', 100)->nullable();
            $table->integer('llm_input_tokens')->nullable();
            $table->integer('llm_output_tokens')->nullable();
            $table->decimal('estimated_cost_usd', 12, 6)->nullable();
            $table->boolean('qa_passed')->default(false);
            $table->integer('pass_score')->default(85);
            $table->timestampsTz();
            $table->index('article_id');
        });

        Schema::create('article_qa_issues', function (Blueprint $table) {
            $table->id();
            $table->foreignId('article_qa_id')->constrained('article_qas')->cascadeOnDelete();
            $table->string('type', 40);
            $table->string('severity', 20);
            $table->text('excerpt');
            $table->text('reason');
            $table->text('suggestion');
            $table->text('section_heading')->nullable();
            $table->jsonb('fact_ids')->default('[]');
            $table->jsonb('source_ids')->default('[]');
            $table->boolean('auto_fixable')->default(false);
            $table->timestampsTz();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('article_qa_issues');
        Schema::dropIfExists('article_qas');
    }
};
