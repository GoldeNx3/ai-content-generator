<?php

namespace Modules\Usage\Services;

use Carbon\CarbonImmutable;
use Modules\Usage\Data\CostReportData;
use Modules\Usage\Queries\CostReportQuery;

final class CostReportService
{
    public function __construct(private readonly CostReportQuery $report) {}

    public function month(int $workspaceId, ?string $month): CostReportData
    {
        $from = $month === null ? CarbonImmutable::now('UTC')->startOfMonth() : CarbonImmutable::createFromFormat('!Y-m', $month, 'UTC');
        $rows = $this->report->execute($workspaceId, $from, $from->addMonth());
        $topics = (int) $rows['articles']->topics;

        return new CostReportData(
            $from->format('Y-m'),
            self::usd($rows['total']->cost),
            (int) $rows['total']->unknown,
            array_map(fn (object $row) => ['kind' => $row->kind, 'jobs' => (int) $row->jobs, 'cost_usd' => self::usd($row->cost)], $rows['kinds']),
            array_map(fn (object $row) => ['stage' => $row->stage, 'calls' => (int) $row->calls, 'cost_usd' => self::usd($row->cost)], $rows['stages']),
            ['topics' => $topics, 'cost_usd' => self::usd($rows['articles']->cost),
                'average_usd' => $topics === 0 ? null : self::usd(bcdiv((string) $rows['articles']->cost, (string) $topics, 6))],
        );
    }

    private static function usd(mixed $value): string
    {
        return bcadd((string) $value, '0', 6);
    }
}
