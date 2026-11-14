<?php

namespace Modules\Sources\Console;

use Illuminate\Console\Command;
use Modules\Sources\Commands\CreateSourceCommand;
use Modules\Sources\Queries\SourceUrlTakenQuery;
use Modules\Workspaces\Exceptions\WorkspaceNotResolvedException;
use Modules\Workspaces\Services\ConsoleWorkspaceResolver;

final class SeedSourcesCommand extends Command
{
    public const GROUPS = [
        'ai' => [
            ['OpenAI', 'https://openai.com/news/rss.xml'],
            ['Anthropic', 'https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml'],
            ['Google AI', 'https://blog.google/technology/ai/rss/'],
            ['Google DeepMind', 'https://deepmind.google/blog/rss.xml'],
            ['Hugging Face', 'https://huggingface.co/blog/feed.xml'],
            ['Microsoft Research', 'https://www.microsoft.com/en-us/research/feed/'],
            ['NVIDIA Developer', 'https://developer.nvidia.com/blog/feed/'],
            ['AWS Machine Learning', 'https://aws.amazon.com/blogs/machine-learning/feed/'],
            ['LangChain', 'https://www.langchain.com/blog/rss.xml'],
            ['Ollama', 'https://ollama.com/blog/rss.xml'],
            ['Simon Willison', 'https://simonwillison.net/atom/entries/'],
            ['Latent Space', 'https://www.latent.space/feed'],
            ['Hacker News: LLM', 'https://hnrss.org/newest?q=LLM&points=100'],
        ],
        'programming' => [
            ['GitHub', 'https://github.blog/feed/'],
            ['Martin Fowler', 'https://martinfowler.com/feed.atom'],
            ['JetBrains', 'https://blog.jetbrains.com/feed/'],
            ['Stack Overflow Blog', 'https://stackoverflow.blog/feed/'],
            ['The Pragmatic Engineer', 'https://newsletter.pragmaticengineer.com/feed'],
            ['InfoQ', 'https://feed.infoq.com/'],
            ['Hacker News: Front Page', 'https://hnrss.org/frontpage?points=300'],
            ['freeCodeCamp', 'https://www.freecodecamp.org/news/rss/'],
            ['Changelog', 'https://changelog.com/feed'],
            ['Netflix Tech Blog', 'https://netflixtechblog.com/feed'],
        ],
        'php' => [
            ['Laravel News', 'https://laravel-news.com/feed'],
            ['Laravel Blog', 'https://blog.laravel.com/feed'],
            ['Symfony Blog', 'https://feeds.feedburner.com/symfony/blog'],
            ['PHP.net', 'https://www.php.net/feed.atom'],
            ['stitcher.io', 'https://stitcher.io/rss'],
            ['freek.dev', 'https://freek.dev/feed'],
            ['Matthias Noback', 'https://matthiasnoback.nl/index.xml'],
            ['dev.to: Laravel', 'https://dev.to/feed/tag/laravel'],
            ['dev.to: Symfony', 'https://dev.to/feed/tag/symfony'],
        ],
        'frontend' => [
            ['React', 'https://react.dev/rss.xml'],
            ['Next.js', 'https://nextjs.org/feed.xml'],
            ['Vue.js', 'https://blog.vuejs.org/feed.rss'],
            ['Nuxt', 'https://nuxt.com/blog/rss.xml'],
            ['Angular', 'https://blog.angular.dev/feed'],
            ['Svelte', 'https://svelte.dev/blog/rss.xml'],
            ['Astro', 'https://astro.build/rss.xml'],
            ['Vite', 'https://vite.dev/blog.rss'],
            ['TypeScript', 'https://devblogs.microsoft.com/typescript/feed/'],
            ['Tailwind CSS', 'https://tailwindcss.com/feeds/feed.xml'],
            ['MDN', 'https://developer.mozilla.org/en-US/blog/rss.xml'],
            ['web.dev', 'https://web.dev/static/blog/feed.xml'],
            ['Chrome for Developers', 'https://developer.chrome.com/static/blog/feed.xml'],
            ['Smashing Magazine', 'https://www.smashingmagazine.com/feed/'],
            ['CSS-Tricks', 'https://css-tricks.com/feed/'],
            ['Frontend Masters', 'https://frontendmasters.com/blog/feed/'],
            ['Josh W. Comeau', 'https://www.joshwcomeau.com/rss.xml'],
            ['Kent C. Dodds', 'https://kentcdodds.com/blog/rss.xml'],
            ['TkDodo', 'https://tkdodo.eu/blog/rss.xml'],
            ['Vercel', 'https://vercel.com/atom'],
            ['dev.to: React', 'https://dev.to/feed/tag/react'],
            ['dev.to: Vue', 'https://dev.to/feed/tag/vue'],
        ],
        'backend' => [
            ['Node.js', 'https://nodejs.org/en/feed/blog.xml'],
            ['Deno', 'https://deno.com/feed'],
            ['Bun', 'https://bun.sh/rss.xml'],
            ['Go', 'https://go.dev/blog/feed.atom'],
            ['Rust', 'https://blog.rust-lang.org/feed.xml'],
            ['Python Insider', 'https://blog.python.org/feeds/posts/default?alt=rss'],
            ['Django', 'https://www.djangoproject.com/rss/weblog/'],
            ['Spring', 'https://spring.io/blog.atom'],
            ['.NET', 'https://devblogs.microsoft.com/dotnet/feed/'],
            ['PostgreSQL', 'https://www.postgresql.org/news.rss'],
            ['Planet PostgreSQL', 'https://planet.postgresql.org/rss20.xml'],
            ['Redis', 'https://redis.io/blog/feed/'],
        ],
        'devops' => [
            ['Kubernetes', 'https://kubernetes.io/feed.xml'],
            ['Docker', 'https://www.docker.com/blog/feed/'],
            ['CNCF', 'https://www.cncf.io/blog/feed/'],
            ['Cloudflare', 'https://blog.cloudflare.com/rss/'],
            ['AWS DevOps', 'https://aws.amazon.com/blogs/devops/feed/'],
            ['AWS Architecture', 'https://aws.amazon.com/blogs/architecture/feed/'],
            ['Azure DevOps', 'https://devblogs.microsoft.com/devops/feed/'],
            ['Microsoft Azure', 'https://azure.microsoft.com/en-us/blog/feed/'],
            ['Google Cloud', 'https://cloudblog.withgoogle.com/rss/'],
            ['HashiCorp', 'https://www.hashicorp.com/blog/feed.xml'],
            ['GitLab', 'https://about.gitlab.com/atom.xml'],
            ['Grafana', 'https://grafana.com/blog/index.xml'],
            ['The New Stack', 'https://thenewstack.io/feed/'],
        ],
        'security' => [
            ['Krebs on Security', 'https://krebsonsecurity.com/feed/'],
            ['Troy Hunt', 'https://www.troyhunt.com/rss/'],
            ['Snyk', 'https://snyk.io/blog/feed/'],
            ['Niebezpiecznik', 'https://niebezpiecznik.pl/feed/'],
            ['Sekurak', 'https://sekurak.pl/feed/'],
            ['Zaufana Trzecia Strona', 'https://zaufanatrzeciastrona.pl/feed/'],
        ],
        'pl' => [
            ['devstyle', 'https://devstyle.pl/feed/'],
            ['Google News: programowanie', 'https://news.google.com/rss/search?q=programowanie&hl=pl&gl=PL&ceid=PL:pl'],
            ['Google News: sztuczna inteligencja', 'https://news.google.com/rss/search?q=sztuczna+inteligencja&hl=pl&gl=PL&ceid=PL:pl'],
            ['Google News: PHP, Laravel, Symfony', 'https://news.google.com/rss/search?q=Laravel+OR+Symfony+OR+PHP&hl=pl&gl=PL&ceid=PL:pl'],
            ['Google News: frontend', 'https://news.google.com/rss/search?q=React+OR+Vue+OR+frontend&hl=pl&gl=PL&ceid=PL:pl'],
            ['Google News: DevOps', 'https://news.google.com/rss/search?q=DevOps+OR+Kubernetes&hl=pl&gl=PL&ceid=PL:pl'],
        ],
        'finance' => [
            ['Subiektywnie o Finansach', 'https://subiektywnieofinansach.pl/feed/'],
            ['Marcin Iwuć', 'https://marciniwuc.com/feed/'],
            ['Jak Oszczędzać Pieniądze', 'https://jakoszczedzacpieniadze.pl/feed/'],
            ['Blogi Bossa', 'https://blogi.bossa.pl/feed/'],
            ['Of Dollars And Data', 'https://ofdollarsanddata.com/feed/'],
            ['A Wealth of Common Sense', 'https://awealthofcommonsense.com/feed/'],
            ['Mr. Money Mustache', 'https://www.mrmoneymustache.com/feed/'],
        ],
    ];

    public const DEFAULT_GROUPS = ['ai', 'programming', 'php', 'frontend', 'backend', 'devops', 'security', 'pl'];

    protected $signature = 'sources:seed
        {--workspace= : ID workspace\'u}
        {--email= : E-mail konta, którego workspace ma dostać źródła}
        {--group=* : Grupy źródeł (domyślnie wszystkie poza finance): ai, programming, php, frontend, backend, devops, security, pl, finance}';

    protected $description = 'Dodaje przykładowe źródła RSS do workspace\'u';

    public function handle(CreateSourceCommand $create, SourceUrlTakenQuery $taken, ConsoleWorkspaceResolver $workspaces): int
    {
        $groups = array_values(array_unique(array_filter(array_map('trim', explode(',', implode(',', $this->option('group')))))));
        $groups = $groups === [] ? self::DEFAULT_GROUPS : $groups;
        $unknown = array_diff($groups, array_keys(self::GROUPS));
        if ($unknown !== []) {
            $this->error('Nieznane grupy: '.implode(', ', $unknown).'. Dostępne: '.implode(', ', array_keys(self::GROUPS)));

            return self::FAILURE;
        }
        try {
            $workspaceId = $workspaces->resolve($this->option('workspace'), $this->option('email'));
        } catch (WorkspaceNotResolvedException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }
        $created = 0;
        $skipped = 0;
        foreach ($groups as $group) {
            foreach (self::GROUPS[$group] as [$name, $url]) {
                if ($taken->execute($url, $workspaceId)) {
                    $skipped++;

                    continue;
                }
                $create->execute($workspaceId, $name, $url, 'rss', true);
                $created++;
            }
        }
        $this->info("Workspace {$workspaceId} (".implode(', ', $groups)."): dodano {$created} źródeł, pominięto {$skipped} istniejących.");

        return self::SUCCESS;
    }
}
