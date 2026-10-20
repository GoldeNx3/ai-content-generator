<?php

namespace Modules\WordPress\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('wordpress_auth_requests', timestamps: false)]
#[Guarded(['id'])]
class WordPressAuthRequest extends Model
{
    protected function casts(): array
    {
        return ['expires_at' => 'immutable_datetime'];
    }
}
