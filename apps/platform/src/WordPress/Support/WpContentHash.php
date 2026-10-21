<?php

namespace Modules\WordPress\Support;

use Modules\WordPress\Exceptions\WordPressException;

final class WpContentHash
{
    public static function ofPost(array $post): string
    {
        $raw = $post['content']['raw'] ?? null;
        if ($raw === null) {
            throw new WordPressException('wordpress_verification_failed');
        }

        return self::ofText($raw);
    }

    public static function ofText(string $text): string
    {
        return hash('sha256', str_replace(["\r\n", "\r"], "\n", $text));
    }
}
