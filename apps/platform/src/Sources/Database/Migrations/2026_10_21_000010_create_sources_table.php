<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('sources', function (Blueprint $table) {
            $table->id();
            $table->foreignId('workspace_id')->constrained()->cascadeOnDelete();
            $table->string('name', 200);
            $table->string('type', 20)->default('rss');
            $table->string('url', 2048);
            $table->boolean('active')->default(true);
            $table->timestampTz('last_fetched_at')->nullable();
            $table->timestampsTz();
            $table->unique(['workspace_id', 'url']);
            $table->unique(['id', 'workspace_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('sources');
    }
};
