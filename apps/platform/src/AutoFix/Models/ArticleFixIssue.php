<?php

namespace Modules\AutoFix\Models;

use Illuminate\Database\Eloquent\Attributes\Guarded;
use Illuminate\Database\Eloquent\Attributes\Table;
use Illuminate\Database\Eloquent\Model;

#[Table('article_fix_issues')]
#[Guarded(['id'])]
class ArticleFixIssue extends Model {}
