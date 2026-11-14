<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement('ALTER TABLE candidates ADD COLUMN embedding real[]');
        DB::statement('ALTER TABLE articles ADD COLUMN embedding real[]');
        Schema::table('candidates', function (Blueprint $table) {
            $table->foreignId('topic_group_id')->nullable()->constrained('candidates')->nullOnDelete();
            $table->float('duplicate_similarity')->nullable();
            $table->index(['workspace_id', 'topic_group_id']);
        });
    }

    public function down(): void
    {
        Schema::table('candidates', function (Blueprint $table) {
            $table->dropIndex(['workspace_id', 'topic_group_id']);
            $table->dropConstrainedForeignId('topic_group_id');
            $table->dropColumn('duplicate_similarity');
        });
        DB::statement('ALTER TABLE articles DROP COLUMN embedding');
        DB::statement('ALTER TABLE candidates DROP COLUMN embedding');
    }
};
