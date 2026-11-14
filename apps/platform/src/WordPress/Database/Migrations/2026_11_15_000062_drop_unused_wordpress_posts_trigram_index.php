<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement('DROP INDEX IF EXISTS wordpress_posts_title_trgm');
    }

    public function down(): void
    {
        DB::statement('CREATE INDEX IF NOT EXISTS wordpress_posts_title_trgm ON wordpress_posts USING gin (title gin_trgm_ops)');
    }
};
