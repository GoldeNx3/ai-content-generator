<?php

namespace Modules\WordPress\Commands;

use Modules\WordPress\Models\WordPressPublication;

final class UpdatePublicationCommand
{
    public function execute(WordPressPublication $publication, array $attributes): void
    {
        $publication->forceFill($attributes)->save();
    }
}
