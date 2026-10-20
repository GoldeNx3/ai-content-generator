<?php

namespace Modules\Pipeline\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('pipeline_job_attempts', timestamps: false)]
#[Fillable(['pipeline_job_id', 'number', 'started_at', 'finished_at', 'outcome', 'error_code', 'error_message', 'last_stage', 'llm_calls'])]
class PipelineJobAttempt extends Model
{
    protected $attributes = ['outcome' => 'running', 'llm_calls' => '[]'];

    protected function casts(): array
    {
        return [
            'llm_calls' => 'array',
            'started_at' => 'immutable_datetime',
            'finished_at' => 'immutable_datetime',
        ];
    }
}
