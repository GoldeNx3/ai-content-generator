<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement('CREATE EXTENSION IF NOT EXISTS pg_trgm');
        Schema::create('wordpress_posts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
            $table->unsignedBigInteger('post_id');
            $table->string('url', 2048);
            $table->string('title', 1000);
            $table->text('excerpt')->nullable();
            $table->timestampTz('synced_at');
            $table->unique(['workspace_id', 'post_id']);
        });
        DB::statement('CREATE INDEX wordpress_posts_title_trgm ON wordpress_posts USING gin (title gin_trgm_ops)');
    }

    public function down(): void
    {
        Schema::dropIfExists('wordpress_posts');
    }
};
