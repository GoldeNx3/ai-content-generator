<?php

return [
    'enabled' => true,
    'directories' => [
        base_path('src') => [
            'namespace' => 'Modules\\',
            'base_path' => base_path('src'),
            'prefix' => 'api',
            'middleware' => 'api',
            'patterns' => ['*Controller.php'],
        ],
    ],
    'middleware' => [
        \Illuminate\Routing\Middleware\SubstituteBindings::class,
    ],
    'scope-bindings' => null,
];
