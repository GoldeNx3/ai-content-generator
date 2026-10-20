<?php

namespace Modules\Sources\Http\Controllers;

use Illuminate\Http\Response;
use Modules\Sources\Models\Source;
use Modules\Sources\Services\SourceService;
use Spatie\RouteAttributes\Attributes\Delete;
use Spatie\RouteAttributes\Attributes\Middleware;

#[Middleware('auth:sanctum')]
final class DeleteSourceController
{
    public function __construct(private readonly SourceService $sources) {}

    #[Delete('sources/{source}')]
    public function __invoke(Source $source): Response
    {
        $this->sources->delete($source);

        return response()->noContent();
    }
}
