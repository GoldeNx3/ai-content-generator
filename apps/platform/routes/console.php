<?php

use Illuminate\Support\Facades\Schedule;

Schedule::command('pipeline:recover')->everyMinute()->withoutOverlapping();
Schedule::command('pipeline:health')->everyMinute()->withoutOverlapping()->onOneServer();

if (config('content.automation.enabled')) {
    Schedule::command('pipeline:scheduled')->everyMinute()->withoutOverlapping()->onOneServer();
}
