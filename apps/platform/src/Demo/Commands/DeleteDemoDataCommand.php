<?php

namespace Modules\Demo\Commands;

use Illuminate\Support\Facades\DB;

final class DeleteDemoDataCommand
{
    /**
     * Kolejność wynika z kluczy RESTRICT: publikacje, poprawki i zadania wskazują na wersje artykułów,
     * a wersje na swoich rodziców. Reszta (research, QA, sugestie) znika kaskadowo z tematem.
     *
     * @param  list<int>  $candidateIds
     */
    public function execute(int $workspaceId, array $candidateIds, string $sourceUrl): int
    {
        if ($candidateIds !== []) {
            $articles = DB::table('articles')->whereIn('candidate_id', $candidateIds)->pluck('id');
            DB::table('wordpress_publications')->whereIn('candidate_id', $candidateIds)->delete();
            DB::table('article_fixes')->whereIn('source_article_version_id', $articles)->delete();
            DB::table('pipeline_jobs')->where('workspace_id', $workspaceId)->whereIn('candidate_id', $candidateIds)->update(['retry_of_job_id' => null]);
            DB::table('pipeline_jobs')->where('workspace_id', $workspaceId)->whereIn('candidate_id', $candidateIds)->delete();
            DB::table('articles')->whereIn('id', $articles)->update(['parent_version_id' => null]);
            DB::table('articles')->whereIn('id', $articles)->delete();
            DB::table('candidates')->where('workspace_id', $workspaceId)->whereIn('id', $candidateIds)->delete();
        }
        DB::table('sources')->where('workspace_id', $workspaceId)->where('url', $sourceUrl)->delete();

        return count($candidateIds);
    }
}
