<?php

namespace Modules\Sources\Console;

use Illuminate\Console\Command;
use Modules\Sources\Commands\CreateSourceCommand;
use Modules\Sources\Queries\SourceUrlTakenQuery;
use Modules\Workspaces\Queries\OldestWorkspaceQuery;

final class SeedSourcesCommand extends Command
{
    private const SOURCES = [
        ['OpenAI', 'https://openai.com/news/rss.xml'],
        ['Anthropic', 'https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml'],
        ['Google AI', 'https://blog.google/technology/ai/rss/'],
        ['Google DeepMind', 'https://deepmind.google/blog/rss.xml'],
        ['Hugging Face', 'https://huggingface.co/blog/feed.xml'],
        ['Microsoft Research', 'https://www.microsoft.com/en-us/research/feed/'],
        ['NVIDIA Developer', 'https://developer.nvidia.com/blog/feed/'],
        ['Simon Willison', 'https://simonwillison.net/atom/entries/'],
        ['GitHub', 'https://github.blog/feed/'],
        ['Martin Fowler', 'https://martinfowler.com/feed.atom'],
        ['JetBrains', 'https://blog.jetbrains.com/feed/'],
        ['Laravel News', 'https://laravel-news.com/feed'],
        ['Symfony Blog', 'https://symfony.com/blog/rss'],
        ['Node.js', 'https://nodejs.org/en/feed/blog.xml'],
        ['React', 'https://react.dev/rss.xml'],
        ['Next.js', 'https://nextjs.org/feed.xml'],
        ['Vue.js', 'https://blog.vuejs.org/feed.rss'],
        ['Svelte', 'https://svelte.dev/blog/rss.xml'],
        ['Astro', 'https://astro.build/rss.xml'],
        ['Tailwind CSS', 'https://tailwindcss.com/feeds/feed.xml'],
        ['MDN', 'https://developer.mozilla.org/en-US/blog/rss.xml'],
        ['web.dev', 'https://web.dev/static/blog/feed.xml'],
        ['Smashing Magazine', 'https://www.smashingmagazine.com/feed/'],
        ['Kubernetes', 'https://kubernetes.io/feed.xml'],
        ['Docker', 'https://www.docker.com/blog/feed/'],
        ['CNCF', 'https://www.cncf.io/blog/feed/'],
        ['Cloudflare', 'https://blog.cloudflare.com/rss/'],
        ['AWS DevOps', 'https://aws.amazon.com/blogs/devops/feed/'],
        ['AWS Architecture', 'https://aws.amazon.com/blogs/architecture/feed/'],
        ['Azure DevOps', 'https://devblogs.microsoft.com/devops/feed/'],
        ['Microsoft Azure', 'https://azure.microsoft.com/en-us/blog/feed/'],
        ['Subiektywnie o Finansach', 'https://subiektywnieofinansach.pl/feed/'],
        ['Marcin Iwuć', 'https://marciniwuc.com/feed/'],
        ['Jak Oszczędzać Pieniądze', 'https://jakoszczedzacpieniadze.pl/feed/'],
        ['Blogi Bossa', 'https://blogi.bossa.pl/feed/'],
        ['Of Dollars And Data', 'https://ofdollarsanddata.com/feed/'],
        ['A Wealth of Common Sense', 'https://awealthofcommonsense.com/feed/'],
        ['Mr. Money Mustache', 'https://www.mrmoneymustache.com/feed/'],
    ];

    protected $signature = 'sources:seed {--workspace= : ID workspace\'u (domyślnie najstarszy)}';

    protected $description = 'Dodaje przykładowe źródła RSS do workspace\'u';

    public function handle(CreateSourceCommand $create, SourceUrlTakenQuery $taken, OldestWorkspaceQuery $oldest): int
    {
        $workspaceId = $this->option('workspace') ? (int) $this->option('workspace') : $oldest->execute()?->id;
        if ($workspaceId === null) {
            $this->error('Brak workspace\'u: najpierw załóż konto.');

            return self::FAILURE;
        }
        $created = 0;
        foreach (self::SOURCES as [$name, $url]) {
            if (! $taken->execute($url, $workspaceId)) {
                $create->execute($workspaceId, $name, $url, 'rss', true);
                $created++;
            }
        }
        $this->info("Dodano {$created} źródeł do workspace'u {$workspaceId}.");

        return self::SUCCESS;
    }
}
