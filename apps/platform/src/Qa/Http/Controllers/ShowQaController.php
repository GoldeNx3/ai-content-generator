<?php

namespace Modules\Qa\Http\Controllers;

use Modules\Articles\Models\Article;
use Modules\Qa\Data\QaReportData;
use Modules\Qa\Services\QaService;
use Spatie\RouteAttributes\Attributes\Get;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class ShowQaController
{
    public function __construct(private readonly QaService $qa) {}

    #[Get('articles/{article}/qa')]
    public function __invoke(Article $article): QaReportData
    {
        return $this->qa->latest($article);
    }
}
