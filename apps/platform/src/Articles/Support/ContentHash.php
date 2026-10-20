<?php

namespace Modules\Articles\Support;

final class ContentHash
{
    public const FIELDS = ['title', 'lead', 'content', 'slug', 'meta_title', 'meta_description'];

    public static function of(array $values): string
    {
        $fields = [];
        foreach (self::FIELDS as $field) {
            $fields[$field] = str_replace(["\r\n", "\r"], "\n", (string) ($values[$field] ?? ''));
        }

        return hash('sha256', CanonicalJson::encode($fields));
    }
}
