<?php

namespace Modules\Pipeline\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Concerns\HasUuids;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Modules\Candidates\Models\Candidate;
use Modules\Pipeline\Enums\JobKind;
use Modules\Pipeline\Enums\JobStatus;

#[Table('pipeline_jobs')]
#[Fillable([
    'id', 'workspace_id', 'candidate_id', 'article_id', 'kind', 'status', 'payload', 'idempotency_key', 'request_hash',
    'stage', 'attempt_count', 'max_attempts', 'available_at', 'started_at', 'finished_at', 'result_type', 'result_id',
    'error_code', 'error_message', 'retry_of_job_id', 'checkpoints',
])]
class PipelineJob extends Model
{
    use HasUuids;

    protected $attributes = ['status' => 'queued', 'checkpoints' => '{}', 'attempt_count' => 0];

    protected function casts(): array
    {
        return [
            'kind' => JobKind::class,
            'status' => JobStatus::class,
            'payload' => 'array',
            'checkpoints' => 'array',
            'available_at' => 'immutable_datetime',
            'started_at' => 'immutable_datetime',
            'finished_at' => 'immutable_datetime',
        ];
    }

    public function candidate(): BelongsTo
    {
        return $this->belongsTo(Candidate::class);
    }

    public function attempts(): HasMany
    {
        return $this->hasMany(PipelineJobAttempt::class)->orderBy('number');
    }

    public function checkpoint(string $key): mixed
    {
        return ($this->checkpoints ?? [])[$key] ?? null;
    }
}
