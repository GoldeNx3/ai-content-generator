<?php

use App\Providers\AppServiceProvider;
use Modules\Pipeline\Providers\PipelineServiceProvider;
use Modules\Shared\Providers\ModulesServiceProvider;
use Modules\Workspaces\Providers\WorkspacesServiceProvider;

return [
    AppServiceProvider::class,
    ModulesServiceProvider::class,
    WorkspacesServiceProvider::class,
    PipelineServiceProvider::class,
];
