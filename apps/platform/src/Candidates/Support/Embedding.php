<?php

namespace Modules\Candidates\Support;

final class Embedding
{
    public static function literal(array $vector): string
    {
        return '{'.implode(',', array_map(fn ($value) => (string) (float) $value, $vector)).'}';
    }
}
