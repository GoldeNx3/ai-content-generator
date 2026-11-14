<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Modules\Shared\Support\UrlNormalizer;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('candidates', function (Blueprint $table) {
            $table->string('url_key', 2048)->nullable();
            $table->index(['workspace_id', 'url_key']);
        });
        DB::table('candidates')->select('id', 'external_url')->orderBy('id')->chunkById(500, function ($rows): void {
            foreach ($rows as $row) {
                DB::table('candidates')->where('id', $row->id)->update(['url_key' => UrlNormalizer::normalize($row->external_url)]);
            }
        });
    }

    public function down(): void
    {
        Schema::table('candidates', function (Blueprint $table) {
            $table->dropIndex(['workspace_id', 'url_key']);
            $table->dropColumn('url_key');
        });
    }
};
