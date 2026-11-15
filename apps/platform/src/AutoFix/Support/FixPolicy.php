<?php

namespace Modules\AutoFix\Support;

final class FixPolicy
{
    private const ALLOWED = ['unsupported_claim', 'title_mismatch', 'repetition', 'style_issue', 'structure_issue', 'seo_issue', 'overclaim', 'too_close_to_source', 'unverified_number'];

    private const CONDITIONAL = ['incorrect_number', 'incorrect_date'];

    public static function eligible(array $issue): bool
    {
        return ($issue['auto_fixable'] ?? false) && in_array($issue['type'], [...self::ALLOWED, ...self::CONDITIONAL], true);
    }
}
