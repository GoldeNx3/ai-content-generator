<?php

use Illuminate\Support\Facades\Schedule;

Schedule::command('pipeline:recover')->everyMinute()->withoutOverlapping();
