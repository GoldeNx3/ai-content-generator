<?php

namespace Modules\Qa\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Modules\Articles\Models\Article;

#[Table('article_qas')]
#[Guarded(['id'])]
class ArticleQa extends Model
{
    protected $attributes = ['status' => 'pending', 'claims' => '[]', 'qa_passed' => false];

    protected function casts(): array
    {
        return [
            'input_snapshot' => 'array',
            'claims' => 'array',
            'qa_passed' => 'boolean',
            'estimated_cost_usd' => 'decimal:6',
        ];
    }

    public function article(): BelongsTo
    {
        return $this->belongsTo(Article::class);
    }

    public function issues(): HasMany
    {
        return $this->hasMany(ArticleQaIssue::class)->orderBy('id');
    }
}
