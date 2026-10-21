<?php

namespace Modules\WordPress\Client;

use Illuminate\Http\Client\Factory as Http;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Support\PublicHostGuard;

final class WordPressClientFactory
{
    public function __construct(private readonly Http $http, private readonly PublicHostGuard $guard) {}

    public function make(ConnectionConfig $config): WordPressClient
    {
        return new WordPressClient($this->http, $this->guard, $config);
    }
}
