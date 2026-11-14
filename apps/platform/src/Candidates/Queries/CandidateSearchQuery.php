<?php

namespace Modules\Candidates\Queries;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Support\Facades\Schema;
use Modules\Candidates\Data\CandidateFiltersData;
use Modules\Candidates\Models\Candidate;
use Modules\Candidates\Support\WorkflowStatusExpression;

final class CandidateSearchQuery
{
    private static ?array $columns = null;

    public function execute(int $workspaceId, CandidateFiltersData $filters): array
    {
        $query = $this->filtered($workspaceId, $filters);
        $total = (clone $query)->count();
        $direction = $filters->order->value;
        $items = $query
            ->select([...self::columns(), 'sources.name as source_name'])
            ->selectRaw(WorkflowStatusExpression::sql().' as workflow_status')
            ->selectRaw('1 + (SELECT COUNT(*) FROM candidates AS members WHERE members.topic_group_id = candidates.id) AS group_size')
            ->join('sources', 'sources.id', '=', 'candidates.source_id')
            ->orderByRaw("candidates.{$filters->sort->value} {$direction} NULLS LAST")
            ->orderByDesc('candidates.created_at')
            ->orderByDesc('candidates.id')
            ->forPage($filters->page, $filters->page_size)
            ->get();

        return [$items, $total];
    }

    private static function columns(): array
    {
        return self::$columns ??= array_map(fn (string $column) => "candidates.{$column}",
            array_values(array_diff(Schema::getColumnListing('candidates'), ['embedding'])));
    }

    private function filtered(int $workspaceId, CandidateFiltersData $filters): Builder
    {
        return Candidate::query()
            ->where('candidates.workspace_id', $workspaceId)
            ->when(! $filters->duplicates && $filters->source_id === null, fn (Builder $q) => $q->whereNull('candidates.topic_group_id'))
            ->when($filters->status, fn (Builder $q) => $q->where('candidates.status', $filters->status->value))
            ->when($filters->workflow_status, fn (Builder $q) => $q->whereRaw(WorkflowStatusExpression::sql().' = ?', [$filters->workflow_status->value]))
            ->when($filters->category, fn (Builder $q) => $q->where('candidates.category', $filters->category->value))
            ->when($filters->source_id !== null, fn (Builder $q) => $q->where('candidates.source_id', $filters->source_id))
            ->when($filters->min_score !== null, fn (Builder $q) => $q->where('candidates.total_score', '>=', $filters->min_score))
            ->when($filters->max_score !== null, fn (Builder $q) => $q->where('candidates.total_score', '<=', $filters->max_score));
    }
}
