<?php

namespace Modules\WordPress\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Modules\Articles\Models\Article;
use Modules\WordPress\Data\SeoSettingsData;
use Modules\WordPress\Services\PublicationService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdatePublicationSettingsController
{
    public function __construct(private readonly PublicationService $publications) {}

    #[Patch('article-versions/{version}/wordpress/settings')]
    public function __invoke(Article $version, Request $request): JsonResponse
    {
        return response()->json($this->publications->updateSettings($version, SeoSettingsData::fromInput($request->all())->values));
    }
}
