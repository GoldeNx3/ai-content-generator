<?php

namespace Modules\WordPress\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('wordpress_publications')]
#[Guarded(['id'])]
class WordPressPublication extends Model
{
    protected $attributes = ['status' => 'not_sent', 'profile' => '{}', 'warnings' => '[]'];

    protected function casts(): array
    {
        return [
            'profile' => 'array',
            'warnings' => 'array',
            'conflict' => 'array',
            'scheduled_at' => 'immutable_datetime',
            'published_at' => 'immutable_datetime',
            'last_synced_at' => 'immutable_datetime',
        ];
    }
}
