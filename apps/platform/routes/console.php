<?php

use Illuminate\Support\Facades\Schedule;

Schedule::command('pipeline:recover')->everyMinute()->withoutOverlapping();

$interval = 30;
if ($interval > 0) {
    Schedule::command('pipeline:scheduled')->cron("*/{$interval} * * * *")->withoutOverlapping()->onOneServer();
}


