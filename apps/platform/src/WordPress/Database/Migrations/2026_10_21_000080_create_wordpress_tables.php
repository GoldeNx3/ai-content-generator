<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('wordpress_connections', function (Blueprint $table) {
            $table->id();
            $table->foreignId('workspace_id')->unique()->constrained()->cascadeOnDelete();
            $table->string('site_url', 2048);
            $table->string('api_url', 2048)->nullable();
            $table->string('username', 200);
            $table->text('app_password');
            $table->string('instance_id', 100)->unique();
            $table->string('seo_plugin', 20)->default('none');
            $table->string('default_status', 20)->default('draft');
            $table->integer('default_author_id')->nullable();
            $table->integer('default_category_id')->nullable();
            $table->integer('wp_user_id')->nullable();
            $table->string('wp_user_name', 200)->nullable();
            $table->boolean('can_publish')->default(false);
            $table->timestampTz('last_checked_at')->nullable();
            $table->string('last_error', 60)->nullable();
            $table->timestampsTz();
        });

        Schema::create('wordpress_auth_requests', function (Blueprint $table) {
            $table->id();
            $table->string('state_hash', 64)->unique();
            $table->foreignId('workspace_id')->index()->constrained()->cascadeOnDelete();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('site_url', 2048);
            $table->string('api_url', 2048)->nullable();
            $table->timestampTz('expires_at');
            $table->timestampTz('created_at')->useCurrent();
        });

        Schema::create('wordpress_publications', function (Blueprint $table) {
            $table->id();
            $table->foreignId('candidate_id')->unique()->constrained()->restrictOnDelete();
            $table->foreignId('article_version_id')->constrained('articles')->restrictOnDelete();
            $table->foreignUuid('job_id')->nullable()->constrained('pipeline_jobs')->nullOnDelete();
            $table->integer('wordpress_post_id')->nullable();
            $table->string('wordpress_instance_id', 100)->nullable();
            $table->text('wordpress_url')->nullable();
            $table->string('status', 20)->default('not_sent');
            $table->string('wp_status', 20)->nullable();
            $table->string('title', 300)->default('');
            $table->string('slug', 300)->default('');
            $table->timestampTz('scheduled_at')->nullable();
            $table->timestampTz('published_at')->nullable();
            $table->timestampTz('last_synced_at')->nullable();
            $table->string('last_synced_content_hash', 64)->nullable();
            $table->integer('media_id')->nullable();
            $table->string('media_fingerprint', 64)->nullable();
            $table->jsonb('profile')->default('{}');
            $table->jsonb('warnings')->default('[]');
            $table->jsonb('conflict')->nullable();
            $table->string('error_code', 60)->nullable();
            $table->timestampsTz();
            $table->unique(['wordpress_instance_id', 'wordpress_post_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('wordpress_publications');
        Schema::dropIfExists('wordpress_auth_requests');
        Schema::dropIfExists('wordpress_connections');
    }
};
