<?php

namespace Modules\Qa\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('article_qa_issues')]
#[Guarded(['id'])]
class ArticleQaIssue extends Model
{
    protected function casts(): array
    {
        return ['fact_ids' => 'array', 'source_ids' => 'array', 'auto_fixable' => 'boolean'];
    }
}
