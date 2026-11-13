<?php

use App\Providers\AppServiceProvider;
use Modules\Auth\Providers\AuthServiceProvider;
use Modules\Pipeline\Providers\PipelineServiceProvider;
use Modules\Shared\Providers\ModulesServiceProvider;
use Modules\Workspaces\Providers\WorkspacesServiceProvider;

return [
    AppServiceProvider::class,
    ModulesServiceProvider::class,
    AuthServiceProvider::class,
    WorkspacesServiceProvider::class,
    PipelineServiceProvider::class,
];
