<?php

namespace Tests\Support;

use Illuminate\Support\Str;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Models\PipelineJob;
use Modules\Sources\Models\Source;

trait BuildsDomain
{
    protected function makeSource(?int $workspaceId = null, string $url = 'https://example.com/feed.xml'): Source
    {
        return Source::query()->firstOrCreate(
            ['workspace_id' => $workspaceId ?? $this->workspace->id, 'url' => $url],
            ['name' => 'Feed '.Str::random(4)],
        );
    }

    protected function makeCandidate(array $attributes = [], ?int $workspaceId = null): Candidate
    {
        $workspaceId ??= $this->workspace->id;
        $source = $this->makeSource($workspaceId);

        return Candidate::query()->create([
            'workspace_id' => $workspaceId,
            'source_id' => $source->id,
            'external_url' => 'https://example.com/'.Str::random(10),
            'title' => 'Temat '.Str::random(5),
            ...$attributes,
        ]);
    }

    protected function makeJob(array $attributes = [], ?Candidate $candidate = null): PipelineJob
    {
        $candidate ??= $this->makeCandidate();

        return PipelineJob::query()->create([
            'workspace_id' => $candidate->workspace_id,
            'candidate_id' => $candidate->id,
            'kind' => 'classify',
            'status' => 'queued',
            'payload' => [],
            'idempotency_key' => (string) Str::uuid(),
            'request_hash' => 'x',
            'available_at' => now(),
            ...$attributes,
        ]);
    }
}
