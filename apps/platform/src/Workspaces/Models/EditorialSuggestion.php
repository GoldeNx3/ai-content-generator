<?php

namespace Modules\Workspaces\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['workspace_id', 'candidate_id', 'job_id', 'kind', 'text', 'why', 'status'])]
class EditorialSuggestion extends Model
{
    protected $attributes = ['status' => 'pending'];
}
