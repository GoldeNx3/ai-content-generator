<?php

namespace Modules\AutoFix\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Modules\Articles\Models\Article;

#[Table('article_fixes')]
#[Guarded(['id'])]
class ArticleFix extends Model
{
    protected $attributes = ['status' => 'pending', 'warnings' => '[]', 'changes' => '[]'];

    protected function casts(): array
    {
        return [
            'input_snapshot' => 'array',
            'warnings' => 'array',
            'changes' => 'array',
            'change_ratio' => 'decimal:6',
            'estimated_cost_usd' => 'decimal:6',
        ];
    }

    public function sourceVersion(): BelongsTo
    {
        return $this->belongsTo(Article::class, 'source_article_version_id');
    }

    public function issues(): HasMany
    {
        return $this->hasMany(ArticleFixIssue::class)->orderBy('id');
    }
}
