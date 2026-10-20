<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('article_fixes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_article_version_id')->index()->constrained('articles')->restrictOnDelete();
            $table->foreignId('result_article_version_id')->nullable()->unique()->constrained('articles')->restrictOnDelete();
            $table->foreignId('qa_id')->constrained('article_qas')->restrictOnDelete();
            $table->foreignUuid('job_id')->nullable()->unique()->constrained('pipeline_jobs')->nullOnDelete();
            $table->string('status', 20)->default('pending');
            $table->integer('iteration');
            $table->string('input_hash', 64);
            $table->jsonb('input_snapshot');
            $table->integer('issues_requested')->default(0);
            $table->integer('issues_fixed')->default(0);
            $table->integer('issues_skipped')->default(0);
            $table->text('summary')->nullable();
            $table->decimal('change_ratio', 8, 6)->nullable();
            $table->jsonb('warnings')->default('[]');
            $table->jsonb('changes')->default('[]');
            $table->string('llm_model', 100)->nullable();
            $table->integer('llm_input_tokens')->nullable();
            $table->integer('llm_output_tokens')->nullable();
            $table->decimal('estimated_cost_usd', 12, 6)->nullable();
            $table->timestampsTz();
        });

        Schema::create('article_fix_issues', function (Blueprint $table) {
            $table->id();
            $table->foreignId('article_fix_id')->constrained('article_fixes')->cascadeOnDelete();
            $table->foreignId('qa_issue_id')->constrained('article_qa_issues')->restrictOnDelete();
            $table->string('status', 20);
            $table->text('reason');
            $table->timestampsTz();
            $table->unique(['article_fix_id', 'qa_issue_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('article_fix_issues');
        Schema::dropIfExists('article_fixes');
    }
};
