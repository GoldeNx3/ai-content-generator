<?php

$classifier = env('OPENAI_CLASSIFIER_MODEL') ?: 'gpt-4.1-mini';
$research = env('OPENAI_RESEARCH_MODEL') ?: $classifier;
$writer = env('OPENAI_WRITER_MODEL') ?: $research;

return [
    'frontend_url' => env('FRONTEND_URL', 'http://localhost:3000'),
    'allow_registration' => (bool) env('ALLOW_REGISTRATION', false),
    'default_monthly_budget_usd' => in_array(env('DEFAULT_MONTHLY_BUDGET_USD', '10'), ['', null], true)
        ? null : (float) env('DEFAULT_MONTHLY_BUDGET_USD', '10'),

    'auth' => [
        'max_login_failures_per_email' => (int) env('AUTH_MAX_FAILURES_PER_EMAIL', 5),
        'max_login_failures_per_ip' => (int) env('AUTH_MAX_FAILURES_PER_IP', 20),
        'max_login_failures_per_email_global' => (int) env('AUTH_MAX_FAILURES_PER_EMAIL_GLOBAL', 50),
        'login_window_minutes' => (int) env('AUTH_WINDOW_MINUTES', 15),
        'max_registrations_per_ip' => (int) env('AUTH_MAX_REGISTRATIONS_PER_IP', 5),
        'registration_window_minutes' => (int) env('AUTH_REGISTRATION_WINDOW_MINUTES', 60),
    ],

    'automation' => [
        'enabled' => (bool) env('AUTOMATION_ENABLED', true),
    ],

    'topics' => [
        'similarity_threshold' => (float) env('TOPIC_SIMILARITY_THRESHOLD', 0.86),
        'window_days' => (int) env('TOPIC_WINDOW_DAYS', 30),
        'max_compared' => (int) env('TOPIC_MAX_COMPARED', 5000),
        'blog_title_similarity' => (float) env('BLOG_TITLE_SIMILARITY', 0.6),
    ],

    'sources' => [
        'allow_private_urls' => (bool) env('SOURCES_ALLOW_PRIVATE_URLS', false),
    ],

    'ingestion' => [
        'fetch_max_age_days' => (int) env('FETCH_MAX_AGE_DAYS', 14),
        'http_timeout_seconds' => (int) env('HTTP_TIMEOUT_SECONDS', 15),
    ],

    'jobs' => [
        'max_attempts' => (int) env('JOB_MAX_ATTEMPTS', 3),
        'timeouts' => [
            'classify' => (int) env('JOB_CLASSIFY_TIMEOUT_SECONDS', 180),
            'research' => (int) env('JOB_RESEARCH_TIMEOUT_SECONDS', 900),
            'write' => (int) env('JOB_WRITE_TIMEOUT_SECONDS', 900),
            'qa_article' => (int) env('JOB_QA_ARTICLE_TIMEOUT_SECONDS', 900),
            'auto_fix_article' => (int) env('JOB_AUTO_FIX_ARTICLE_TIMEOUT_SECONDS', 900),
            'prepare_wordpress' => (int) env('JOB_PREPARE_WORDPRESS_TIMEOUT_SECONDS', 300),
            'publish_wordpress' => (int) env('JOB_PUBLISH_WORDPRESS_TIMEOUT_SECONDS', 600),
        ],
        'backoff_seconds' => [10, 30, 90],
    ],

    'ai' => [
        'python' => env('AI_PYTHON', 'python3'),
        'workdir' => env('AI_WORKDIR', base_path('../api')),
        'openai_api_key' => env('OPENAI_API_KEY', ''),
        'tavily_api_key' => env('TAVILY_API_KEY', ''),
        'models' => [
            'classifier' => $classifier,
            'research' => $research,
            'brief' => env('OPENAI_BRIEF_MODEL') ?: $research,
            'writer' => $writer,
            'qa' => env('OPENAI_QA_MODEL') ?: $research,
            'auto_fix' => env('OPENAI_AUTO_FIX_MODEL') ?: $writer,
            'embedding' => env('OPENAI_EMBEDDING_MODEL') ?: 'text-embedding-3-small',
        ],
        'settings' => [
            'search_provider' => env('SEARCH_PROVIDER', 'manual'),
            'tavily_search_depth' => env('TAVILY_SEARCH_DEPTH', 'advanced'),
            'tavily_credit_usd' => (float) env('TAVILY_CREDIT_USD', 0.008),
            'llm_timeout_seconds' => (float) env('LLM_TIMEOUT_SECONDS', 60),
            'research_timeout_seconds' => (float) env('RESEARCH_TIMEOUT_SECONDS', 300),
            'writer_timeout_seconds' => (float) env('WRITER_TIMEOUT_SECONDS', 300),
            'qa_timeout_seconds' => (float) env('QA_TIMEOUT_SECONDS', 300),
            'auto_fix_timeout_seconds' => (float) env('AUTO_FIX_TIMEOUT_SECONDS', 300),
            'page_fetch_timeout_seconds' => (float) env('PAGE_FETCH_TIMEOUT_SECONDS', 20),
            'page_max_bytes' => (int) env('PAGE_MAX_BYTES', 5_000_000),
            'raw_content_max_chars' => (int) env('RAW_CONTENT_MAX_CHARS', 300_000),
            'research_max_extra_sources' => (int) env('RESEARCH_MAX_EXTRA_SOURCES', 8),
            'research_max_chars_per_source' => (int) env('RESEARCH_MAX_CHARS_PER_SOURCE', 12_000),
            'research_max_chars_original' => (int) env('RESEARCH_MAX_CHARS_ORIGINAL', 20_000),
            'research_max_total_chars' => (int) env('RESEARCH_MAX_TOTAL_CHARS', 60_000),
            'research_max_facts' => (int) env('RESEARCH_MAX_FACTS', 60),
            'qa_pass_score' => (int) env('QA_PASS_SCORE', 85),
            'qa_max_source_overlap' => (float) env('QA_MAX_SOURCE_OVERLAP', 0.15),
            'auto_fix_max_change_ratio' => (float) env('AUTO_FIX_MAX_CHANGE_RATIO', 0.35),
            'auto_fix_max_iterations' => (int) env('AUTO_FIX_MAX_ITERATIONS', 2),
        ],
        'pricing' => [
            'gpt-6.1-sol' => ['input' => 2.00, 'cached_input' => 0.10, 'output' => 10.00, 'long_context_threshold' => 272000, 'long_input' => 4.00, 'long_output' => 15.00, 'long_cached_input' => 0.20],
            'gpt-4.1' => ['input' => 2.00, 'output' => 8.00],
            'gpt-4.1-mini' => ['input' => 0.40, 'cached_input' => 0.10, 'output' => 1.60],
            'gpt-4.1-nano' => ['input' => 0.10, 'output' => 0.40],
            'gpt-4o' => ['input' => 2.50, 'output' => 10.00],
            'gpt-4o-mini' => ['input' => 0.15, 'output' => 0.60],
            'gpt-5' => ['input' => 1.25, 'output' => 10.00],
            'gpt-5-mini' => ['input' => 0.25, 'output' => 2.00],
            'gpt-5-nano' => ['input' => 0.05, 'output' => 0.40],
            'text-embedding-3-small' => ['input' => 0.02, 'output' => 0.0],
        ],
    ],

    'wordpress' => [
        'timeout_seconds' => (int) env('WORDPRESS_TIMEOUT_SECONDS', 30),
        'allow_private_urls' => (bool) env('WORDPRESS_ALLOW_PRIVATE_URLS', false),
        'asset_root' => env('WORDPRESS_ASSET_ROOT', storage_path('app/assets')),
        'max_image_bytes' => (int) env('WORDPRESS_MAX_IMAGE_BYTES', 10_000_000),
        'import' => [
            'url' => env('WORDPRESS_URL'),
            'api_url' => env('WORDPRESS_API_URL'),
            'username' => env('WORDPRESS_USERNAME'),
            'app_password' => env('WORDPRESS_APP_PASSWORD'),
        ],
    ],
];
