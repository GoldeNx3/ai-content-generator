<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    private const TRACKING_PREFIXES = ['utm_', 'mc_', 'fbclid', 'gclid', 'ref_src'];

    public function up(): void
    {
        Schema::table('candidates', function (Blueprint $table) {
            $table->string('url_key', 2048)->nullable();
            $table->index(['workspace_id', 'url_key']);
        });
        DB::table('candidates')->select('id', 'external_url')->orderBy('id')->chunkById(500, function ($rows): void {
            $values = [];
            $bindings = [];
            foreach ($rows as $row) {
                $values[] = '(?::bigint, ?)';
                array_push($bindings, $row->id, $this->normalize($row->external_url));
            }
            DB::update('UPDATE candidates SET url_key = v.url_key FROM (VALUES '.implode(', ', $values).') AS v(id, url_key) WHERE candidates.id = v.id', $bindings);
        });
    }

    public function down(): void
    {
        Schema::table('candidates', function (Blueprint $table) {
            $table->dropIndex(['workspace_id', 'url_key']);
            $table->dropColumn('url_key');
        });
    }

    private function normalize(string $url): string
    {
        $parts = parse_url(trim($url)) ?: [];
        $host = strtolower($parts['host'] ?? '');
        if (str_starts_with($host, 'www.')) {
            $host = substr($host, 4);
        }
        if (isset($parts['port']) && ! in_array($parts['port'], [80, 443], true)) {
            $host .= ':'.$parts['port'];
        }
        $pairs = [];
        foreach (explode('&', $parts['query'] ?? '') as $pair) {
            if ($pair === '') {
                continue;
            }
            $name = strtolower(urldecode(explode('=', $pair, 2)[0]));
            foreach (self::TRACKING_PREFIXES as $prefix) {
                if (str_starts_with($name, $prefix)) {
                    continue 2;
                }
            }
            $pairs[] = $pair;
        }
        $scheme = in_array($parts['scheme'] ?? '', ['http', 'https'], true) ? 'https' : ($parts['scheme'] ?? '');
        $path = rtrim($parts['path'] ?? '', '/');

        return $scheme.'://'.$host.$path.($pairs === [] ? '' : '?'.implode('&', $pairs));
    }
};
