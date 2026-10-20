<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('researches', function (Blueprint $table) {
            $table->id();
            $table->foreignId('candidate_id')->unique()->constrained()->cascadeOnDelete();
            $table->foreignUuid('job_id')->nullable()->constrained('pipeline_jobs')->nullOnDelete();
            $table->string('status', 20)->default('pending');
            $table->text('summary')->nullable();
            $table->text('why_it_matters')->nullable();
            $table->text('suggested_angle')->nullable();
            $table->jsonb('search_queries')->default('[]');
            $table->jsonb('uncertainties')->default('[]');
            $table->jsonb('conflicts')->default('[]');
            $table->text('error')->nullable();
            $table->string('llm_model', 100)->nullable();
            $table->integer('llm_input_tokens')->default(0);
            $table->integer('llm_output_tokens')->default(0);
            $table->decimal('estimated_cost_usd', 12, 6)->nullable();
            $table->timestampTz('started_at')->nullable();
            $table->timestampTz('completed_at')->nullable();
            $table->timestampsTz();
        });

        Schema::create('research_sources', function (Blueprint $table) {
            $table->id();
            $table->foreignId('research_id')->constrained('researches')->cascadeOnDelete();
            $table->string('url', 2048);
            $table->string('origin', 20);
            $table->string('title', 1000)->nullable();
            $table->string('publisher', 300)->nullable();
            $table->string('source_type', 20)->default('other');
            $table->integer('source_score')->default(40);
            $table->timestampTz('published_at')->nullable();
            $table->text('raw_content')->nullable();
            $table->text('extracted_content')->nullable();
            $table->string('fetch_status', 20)->default('pending');
            $table->integer('http_status')->nullable();
            $table->text('error')->nullable();
            $table->timestampsTz();
            $table->unique(['research_id', 'url']);
        });

        Schema::create('research_facts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('research_id')->constrained('researches')->cascadeOnDelete();
            $table->text('claim');
            $table->string('importance', 20);
            $table->integer('confidence');
            $table->timestampsTz();
        });

        Schema::create('research_fact_sources', function (Blueprint $table) {
            $table->foreignId('fact_id')->constrained('research_facts')->cascadeOnDelete();
            $table->foreignId('source_id')->constrained('research_sources')->cascadeOnDelete();
            $table->primary(['fact_id', 'source_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('research_fact_sources');
        Schema::dropIfExists('research_facts');
        Schema::dropIfExists('research_sources');
        Schema::dropIfExists('researches');
    }
};
