<?php

namespace Modules\Pipeline\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('pipeline_job_batches', keyType: 'string', incrementing: false, timestamps: false)]
#[Fillable(['id', 'workspace_id', 'request_hash', 'candidate_ids', 'skipped_ids'])]
class PipelineJobBatch extends Model
{
    protected function casts(): array
    {
        return ['candidate_ids' => 'array', 'skipped_ids' => 'array'];
    }
}
