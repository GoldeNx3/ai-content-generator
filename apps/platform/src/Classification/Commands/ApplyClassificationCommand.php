<?php

namespace Modules\Classification\Commands;

use Carbon\CarbonImmutable;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Support\CallUsage;

final class ApplyClassificationCommand
{
    public function execute(int $candidateId, string $jobId, array $result, CallUsage $usage, ?array $coveredBy): void
    {
        Candidate::query()->whereKey($candidateId)->update([
            'relevance_score' => $result['relevance'],
            'freshness_score' => $result['freshness'],
            'search_potential_score' => $result['search_potential'],
            'commercial_potential_score' => $result['commercial_potential'],
            'total_score' => $result['total_score'],
            'category' => $result['category'],
            'llm_reason' => $result['reason'],
            'covered_by' => $coveredBy === null ? null : json_encode($coveredBy, JSON_THROW_ON_ERROR),
            'llm_model' => $usage->model,
            'llm_input_tokens' => $usage->inputTokens,
            'llm_output_tokens' => $usage->outputTokens,
            'estimated_cost_usd' => $usage->costUsd,
            'classified_at' => CarbonImmutable::now(),
            'classification_job_id' => $jobId,
            'updated_at' => CarbonImmutable::now(),
        ]);
    }
}
