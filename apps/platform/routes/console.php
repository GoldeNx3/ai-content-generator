<?php

use Illuminate\Support\Facades\Schedule;

Schedule::command('pipeline:recover')->everyMinute()->withoutOverlapping();

$interval = (int) config('content.ingestion.fetch_interval_minutes');
if ($interval > 0) {
    Schedule::command('pipeline:scheduled')->cron("*/{$interval} * * * *")->withoutOverlapping()->onOneServer();
}


