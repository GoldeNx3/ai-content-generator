<?php

namespace Modules\Articles\Commands;

use Modules\Articles\Models\Article;

final class SaveSeoPreviewCommand
{
    public function execute(Article $article, array $preview, string $origin): void
    {
        $article->update(['seo_preview' => $preview, 'seo_origin' => $origin]);
    }
}
