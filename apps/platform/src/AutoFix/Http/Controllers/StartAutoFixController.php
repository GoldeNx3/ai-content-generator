<?php

namespace Modules\AutoFix\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\AutoFix\Data\FixRequestData;
use Modules\AutoFix\Services\AutoFixService;
use Modules\Pipeline\Support\IdempotencyKey;
use Modules\Pipeline\Support\JobResponse;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Post;

#[Middleware('auth:sanctum')]
final class StartAutoFixController
{
    public function __construct(private readonly AutoFixService $autoFix) {}

    #[Post('article-versions/{version}/auto-fix')]
    public function __invoke(Article $version, FixRequestData $data, Request $request): JsonResponse
    {
        return JobResponse::accepted($this->autoFix->fix($version, $data->issue_ids, IdempotencyKey::from($request)));
    }
}
