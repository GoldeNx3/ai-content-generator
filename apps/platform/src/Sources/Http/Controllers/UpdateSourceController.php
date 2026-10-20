<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Modules\Sources\Data\UpdateSourceData;
use Modules\Sources\Models\Source;
use Modules\Sources\Services\SourceService;
use Spatie\RouteAttributes\Attributes\Middleware;
use Spatie\RouteAttributes\Attributes\Patch;

#[Middleware('auth:sanctum')]
final class UpdateSourceController
{
    public function __construct(private readonly SourceService $sources) {}

    #[Patch('sources/{source}')]
    public function __invoke(Source $source, UpdateSourceData $data): JsonResponse
    {
        return response()->json($this->sources->update($source, $data));
    }
}
