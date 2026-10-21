<?php

namespace Modules\AutoFix\Http\Controllers;

use Modules\AutoFix\Data\FixData;
use Modules\AutoFix\Models\ArticleFix;
use Modules\AutoFix\Services\AutoFixService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowFixController
{
    public function __construct(private readonly AutoFixService $autoFix) {}

    #[Get('article-fixes/{fix}')]
    public function __invoke(ArticleFix $fix): FixData
    {
        return $this->autoFix->show($fix);
    }
}
