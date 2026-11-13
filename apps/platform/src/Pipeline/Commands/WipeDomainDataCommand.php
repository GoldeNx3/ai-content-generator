<?php

namespace Modules\Pipeline\Commands;

use Illuminate\Support\Facades\DB;

final class WipeDomainDataCommand
{
    private const TABLES = [
        'pipeline_job_attempts', 'pipeline_jobs', 'pipeline_job_batches', 'failed_jobs',
        'wordpress_publications', 'article_fix_issues', 'article_fixes', 'article_qa_issues', 'article_qas', 'articles',
        'research_fact_sources', 'research_facts', 'research_sources', 'researches',
        'candidates', 'sources',
    ];

    public function execute(): void
    {
        DB::statement('TRUNCATE TABLE '.implode(', ', self::TABLES).' RESTART IDENTITY CASCADE');
    }
}
