<?php

namespace Modules\WordPress\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('wordpress_connections')]
#[Guarded(['id'])]
#[Hidden(['app_password'])]
class WordPressConnection extends Model
{
    protected $attributes = ['seo_plugin' => 'none', 'default_status' => 'draft', 'can_publish' => false];

    protected function casts(): array
    {
        return ['app_password' => 'encrypted', 'can_publish' => 'boolean', 'last_checked_at' => 'immutable_datetime', 'posts_synced_at' => 'immutable_datetime'];
    }
}
