<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('candidates', function (Blueprint $table) {
            $table->id();
            $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
            $table->unsignedBigInteger('source_id')->index();
            $table->string('external_url', 2048);
            $table->string('title', 1000);
            $table->text('summary')->nullable();
            $table->timestampTz('original_published_at')->nullable();
            $table->string('status', 20)->default('pending')->index();
            $table->integer('relevance_score')->nullable();
            $table->integer('freshness_score')->nullable();
            $table->integer('search_potential_score')->nullable();
            $table->integer('commercial_potential_score')->nullable();
            $table->integer('total_score')->nullable()->index();
            $table->string('category', 20)->nullable();
            $table->text('llm_reason')->nullable();
            $table->string('llm_model', 200)->nullable();
            $table->integer('llm_input_tokens')->nullable();
            $table->integer('llm_output_tokens')->nullable();
            $table->decimal('estimated_cost_usd', 12, 6)->nullable();
            $table->timestampTz('classified_at')->nullable();
            $table->uuid('classification_job_id')->nullable();
            $table->timestampsTz();
            $table->foreign(['source_id', 'workspace_id'])->references(['id', 'workspace_id'])->on('sources')->cascadeOnDelete();
            $table->unique(['workspace_id', 'external_url']);
            $table->unique(['id', 'workspace_id']);
            $table->index(['workspace_id', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('candidates');
    }
};
