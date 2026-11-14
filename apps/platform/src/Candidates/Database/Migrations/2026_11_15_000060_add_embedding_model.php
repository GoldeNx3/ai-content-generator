<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        foreach (['candidates', 'articles'] as $table) {
            Schema::table($table, function (Blueprint $table) {
                $table->string('embedding_model', 100)->nullable();
            });
        }
    }

    public function down(): void
    {
        foreach (['candidates', 'articles'] as $table) {
            Schema::table($table, function (Blueprint $table) {
                $table->dropColumn('embedding_model');
            });
        }
    }
};
