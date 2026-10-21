<?php

namespace Modules\WordPress\Data;

use Illuminate\Support\Facades\Validator;
use Spatie\LaravelData\Data;

final class SeoSettingsData extends Data
{
    public const FIELDS = [
        'title', 'slug', 'seo_title', 'meta_description', 'excerpt', 'canonical_url', 'focus_keyword', 'secondary_keywords',
        'og_title', 'og_description', 'twitter_title', 'twitter_description', 'robots_index', 'robots_follow', 'schema_type',
        'category', 'tags', 'author_id', 'featured_image_url', 'featured_image_asset', 'internal_links', 'faq', 'howto_steps',
        'include_sources',
    ];

    public function __construct(public array $values) {}

    public static function rules(): array
    {
        return [
            'excerpt' => ['sometimes', 'string', 'max:1000'],
            'canonical_url' => ['prohibited'],
            'focus_keyword' => ['sometimes', 'string', 'max:200'],
            'secondary_keywords' => ['sometimes', 'array', 'max:20'],
            'secondary_keywords.*' => ['string', 'max:100'],
            'og_title' => ['sometimes', 'string', 'max:300'],
            'og_description' => ['sometimes', 'string', 'max:500'],
            'twitter_title' => ['sometimes', 'string', 'max:300'],
            'twitter_description' => ['sometimes', 'string', 'max:500'],
            'robots_index' => ['sometimes', 'boolean'],
            'robots_follow' => ['sometimes', 'boolean'],
            'schema_type' => ['sometimes', 'in:Article,NewsArticle,TechArticle,HowTo,FAQPage'],
            'category' => ['sometimes', 'nullable', 'in:AI,Modele AI,Programowanie,Narzędzia AI,Automatyzacja,Biznes,Newsy,Poradniki,Porównania'],
            'tags' => ['sometimes', 'array', 'max:8'],
            'tags.*' => ['string', 'max:50'],
            'author_id' => ['sometimes', 'nullable', 'integer', 'min:1'],
            'featured_image_url' => ['sometimes', 'nullable', 'url:http,https', 'max:2048'],
            'featured_image_asset' => ['sometimes', 'nullable', 'string', 'max:500'],
            'internal_links' => ['sometimes', 'array', 'max:20'],
            'faq' => ['sometimes', 'array', 'max:20'],
            'howto_steps' => ['sometimes', 'array', 'max:30'],
            'include_sources' => ['sometimes', 'boolean'],
        ];
    }

    public static function fromInput(array $input): self
    {
        $valid = Validator::make($input, self::rules())->validate();

        return new self(array_intersect_key($valid, array_flip(self::FIELDS)));
    }
}
