<?php

namespace Modules\Research\Commands;

use Carbon\CarbonImmutable;
use Modules\Research\Models\ResearchSource;

final class ApplySourceExtractionCommand
{
    public function execute(ResearchSource $source, array $extraction): void
    {
        $success = ($extraction['fetch_status'] ?? 'failed') === 'success';
        $source->forceFill([
            'source_type' => $extraction['source_type'],
            'source_score' => $extraction['source_score'],
            'fetch_status' => $extraction['fetch_status'],
            'http_status' => $extraction['http_status'] ?? null,
            'error' => $extraction['error'] ?? null,
            ...($success ? [
                'title' => $extraction['title'] ?? $source->title,
                'publisher' => $extraction['publisher'] ?? null,
                'published_at' => isset($extraction['published_at']) ? CarbonImmutable::parse($extraction['published_at']) : null,
                'extracted_content' => $extraction['extracted_content'] ?? null,
                'raw_content' => $extraction['raw_content'] ?? null,
            ] : []),
        ])->save();
    }
}
