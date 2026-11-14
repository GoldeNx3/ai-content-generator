<?php

namespace Modules\Articles\Commands;

use Illuminate\Support\Facades\DB;
use Modules\Candidates\Support\Embedding;

final class StoreArticleEmbeddingCommand
{
    public function execute(int $articleId, array $vector, ?string $model): void
    {
        DB::table('articles')->where('id', $articleId)->update(['embedding' => Embedding::literal($vector), 'embedding_model' => $model]);
    }
}
