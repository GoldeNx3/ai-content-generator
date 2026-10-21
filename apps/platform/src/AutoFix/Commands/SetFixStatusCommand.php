<?php

namespace Modules\AutoFix\Commands;

use Modules\AutoFix\Models\ArticleFix;

final class SetFixStatusCommand
{
    public function execute(ArticleFix $fix, string $status): void
    {
        $fix->update(['status' => $status]);
    }
}
