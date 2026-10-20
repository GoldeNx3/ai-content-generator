<?php

namespace Modules\Pipeline\Services;

use Illuminate\Contracts\Container\Container;
use Modules\Pipeline\Contracts\StageHandler;
use Modules\Pipeline\Enums\JobKind;

final class HandlerRegistry
{
    public function __construct(private readonly Container $container, private readonly array $handlers) {}

    public function for(JobKind $kind): StageHandler
    {
        return $this->container->make($this->handlers[$kind->value]);
    }
}
