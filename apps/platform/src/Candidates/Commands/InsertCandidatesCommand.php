<?php

namespace Modules\Candidates\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

final class InsertCandidatesCommand
{
    private const CHUNK = 500;

    public function execute(array $rows): int
    {
        $now = CarbonImmutable::now();
        $inserted = 0;
        foreach (array_chunk($rows, self::CHUNK) as $chunk) {
            $inserted += DB::table('candidates')->insertOrIgnore(array_map(
                fn (array $row) => ['status' => 'pending', ...$row, 'created_at' => $now, 'updated_at' => $now],
                $chunk,
            ));
        }

        return $inserted;
    }
}
