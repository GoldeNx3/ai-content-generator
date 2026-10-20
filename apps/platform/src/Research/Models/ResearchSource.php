<?php

namespace Modules\Research\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Model;
use Modules\Research\Enums\FetchStatus;
use Modules\Research\Enums\SourceOrigin;

#[Fillable([
    'research_id', 'url', 'origin', 'title', 'publisher', 'source_type', 'source_score', 'published_at',
    'raw_content', 'extracted_content', 'fetch_status', 'http_status', 'error',
])]
#[Hidden(['raw_content'])]
class ResearchSource extends Model
{
    protected $attributes = ['source_type' => 'other', 'source_score' => 40, 'fetch_status' => 'pending'];

    protected function casts(): array
    {
        return [
            'origin' => SourceOrigin::class,
            'fetch_status' => FetchStatus::class,
            'published_at' => 'immutable_datetime',
        ];
    }
}
