<?php

namespace Modules\Candidates\Commands;

use Modules\Candidates\Models\Candidate;

final class SaveEditorTakeCommand
{
    public function execute(Candidate $candidate, ?string $take): void
    {
        $candidate->forceFill(['editor_take' => $take])->save();
    }
}
