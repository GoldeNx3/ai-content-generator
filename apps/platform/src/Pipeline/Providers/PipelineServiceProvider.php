<?php

namespace Modules\Pipeline\Providers;

use Illuminate\Contracts\Container\Container;
use Illuminate\Support\ServiceProvider;
use Modules\Articles\Handlers\WriteHandler;
use Modules\AutoFix\Handlers\AutoFixHandler;
use Modules\Classification\Handlers\ClassifyHandler;
use Modules\Pipeline\Services\HandlerRegistry;
use Modules\Qa\Handlers\QaHandler;
use Modules\Research\Handlers\ResearchHandler;
use Modules\WordPress\Handlers\PrepareWordPressHandler;
use Modules\WordPress\Handlers\PublishWordPressHandler;

final class PipelineServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(HandlerRegistry::class, fn (Container $app) => new HandlerRegistry($app, [
            'classify' => ClassifyHandler::class,
            'research' => ResearchHandler::class,
            'write' => WriteHandler::class,
            'qa_article' => QaHandler::class,
            'auto_fix_article' => AutoFixHandler::class,
            'prepare_wordpress' => PrepareWordPressHandler::class,
            'publish_wordpress' => PublishWordPressHandler::class,
        ]));
    }
}
