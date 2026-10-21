# AI Content Engine

Zbiera wpisy ze źródeł RSS/Atom, ocenia je przez LLM, a dla wybranych tematów wykonuje research, pisze
artykuł, sprawdza go (QA), poprawia (Auto Fix), czeka na akceptację człowieka i publikuje w WordPressie.

```text
RSS → kandydaci → ocena → research → artykuł → QA → Auto Fix → akceptacja → WordPress
```

| Część | Technologia | Rola |
|---|---|---|
| `apps/platform` | Laravel 13, PostgreSQL 17, Redis | API, auth, workspace'y, kolejka, scheduler, RSS, WordPress |
| `apps/ai` | Python 3.13 (CLI `python -m ai`) | obliczenia AI na treści: ocena, research, pisanie, QA, Auto Fix, SEO, HTML |
| `apps/web` | Next.js 16, React 19, Tailwind 4 | panel |
| `integrations/wordpress` | PHP | wtyczka Content Engine Bridge |

Architektura, kontrakt zadań AI i kolejka: [docs/platform/README.md](docs/platform/README.md).

## Start

Wymagania: Docker + Docker Compose v2.

```bash
cp .env.example .env                                   # tylko NEXT_PUBLIC_API_URL dla dev
cp apps/platform/.env.example apps/platform/.env       # uzupełnij OPENAI_API_KEY
make up                                                # db, redis, migracja, platform, queue, scheduler, web
docker compose exec platform php artisan key:generate
make seed-demo                                         # po rejestracji pierwszego konta: tematy demo bez kosztów AI
```

| Usługa | Adres |
|---|---|
| Panel | http://localhost:3000 (rejestracja: `/register`) |
| API | http://localhost:8000/api |
| PostgreSQL | localhost:5432 (`content` / `content`) |

`make dev` uruchamia panel przez `next dev` z montowanym `apps/web` (hot reload). Kod Laravela i Pythona jest
montowany wolumenem; po zmianach PHP w kolejce/schedulerze: `docker compose restart queue scheduler`.
Produkcyjny build panelu po zmianach: `docker compose up -d --build web`.

## Komendy

```text
make up / dev / down / logs / build
make migrate                    php artisan migrate (usługa migrate działa też przy starcie)
make test                       test-platform (PHPUnit) + test-ai (pytest)
make seed WORKSPACE=<id>        przykładowe źródła RSS (domyślnie najstarszy workspace)
make seed-demo WORKSPACE=<id>   tematy demo: pełny pipeline za 0 USD
make pipeline                   jednorazowo to, co scheduler: RSS + zlecenie oceny
make create-user EMAIL=...      konto bez rejestracji; WORKSPACE=<id> dołącza jako owner
make set-budget WORKSPACE=<id> USD=<kwota|default>
make wipe                       kopia bazy do /tmp, usunięcie danych i zadań kolejki (konta zostają)
make artisan CMD="route:list"
```

## Konfiguracja

Dev: `apps/platform/.env`. Prod: root `.env` (opis w `.env.example`). Najważniejsze zmienne:

| Zmienna | Opis |
|---|---|
| `OPENAI_API_KEY` | klucz OpenAI (Laravel przekazuje go procesowi AI) |
| `OPENAI_*_MODEL` | modele etapów: classifier, research, brief, writer, qa, auto_fix (puste = model poprzedniego etapu) |
| `SEARCH_PROVIDER`, `TAVILY_API_KEY` | `manual` (źródła dodawane ręcznie) albo `tavily` |
| `FETCH_INTERVAL_MINUTES` | co ile minut scheduler pobiera RSS i zleca ocenę (`0` = wyłączony) |
| `FETCH_MAX_AGE_DAYS`, `CLASSIFY_BATCH_LIMIT` | filtr wieku wpisów i limit ocen na przebieg |
| `DEFAULT_MONTHLY_BUDGET_USD` | miesięczny budżet AI workspace'u (domyślnie 10; puste = bez limitu) |
| `ALLOW_REGISTRATION` | publiczna rejestracja (każde konto dostaje własny workspace) |
| `QA_PASS_SCORE`, `AUTO_FIX_MAX_*` | próg QA i limity Auto Fix |
| `FRONTEND_URL`, `SANCTUM_STATEFUL_DOMAINS`, `SESSION_DOMAIN` | origin panelu (CORS + CSRF) i ciasteczko sesji `ce_session` |
| `WORDPRESS_ALLOW_PRIVATE_URLS` | `true` tylko dla lokalnego WP w sieci Dockera (ochrona SSRF) |

Pełna lista z wartościami domyślnymi: `apps/platform/config/content.php`.

## Jak działa pipeline

Każdy płatny krok (`classify`, `research`, `write`, `qa_article`, `auto_fix_article`, `prepare_wordpress`,
`publish_wordpress`) to **job**: API zapisuje go w PostgreSQL, zwraca `202` i wrzuca do kolejki Redis. Worker
Laravela (`queue:work`) uruchamia kolejne zadania Pythona, zapisuje wynik każdego kroku jako checkpoint i na końcu
utrwala wynik. Zamknięcie przeglądarki ani restart API nie przerywa pracy; przerwane joby wracają do kolejki
(`pipeline:recover`). Etapy nie uruchamiają się same – każdy kolejny krok zleca człowiek.

- **Ocena**: cztery oceny 0–100, kategoria i uzasadnienie;
  `total_score = round(relevance*0.40 + freshness*0.20 + search_potential*0.25 + commercial_potential*0.15)`.
- **Research**: pobranie oryginału i podlinkowanych materiałów (bez rekursywnego crawla), opcjonalnie
  wyszukiwarka, ocena wiarygodności źródeł wg domeny, fakty wyłącznie z przekazanych URL-i (fakt bez poprawnego
  źródła trafia do niepewności). Pobieranie stron sprawdza publiczne adresy. Źródła można dodawać ręcznie.
- **Artykuł**: brief (format, kąt, plan sekcji, wymagane fakty), potem tekst z referencjami do faktów i źródeł.
  Walidacja usuwa ID spoza researchu i ostrzega o liczbach bez pokrycia. Każda generacja i edycja to nowa wersja.
- **QA i Auto Fix**: [docs/qa](docs/qa/README.md), [docs/auto-fix](docs/auto-fix/README.md),
  [czytelność](docs/readability/README.md).
- **WordPress**: połączenie per workspace w panelu (`/settings`), publikacja zatwierdzonej wersji z aktualnym
  QA, domyślnie jako szkic: [docs/wordpress](docs/wordpress/README.md).
- **Demo**: tematy z przestrzeni `https://demo.content-engine.invalid/` przechodzą cały pipeline na stałych
  odpowiedziach, bez wywołań AI: [docs/demo](docs/demo/README.md).

Koszty: każde wywołanie LLM jest zapisane w próbie joba z tokenami i kosztem z cennika (`LLM_PRICING`).
Wywołanie przerwane w trakcie ma koszt nieznany (nie zerowy). Panel **Kolejka** (`/queue`) pokazuje historię
jobów, próby, wywołania i koszty; zadanie zakończone błędem można ponowić.

## Testy

```bash
make test                         # PHPUnit (baza content_test) + pytest modułów AI
cd apps/web && npm test           # testy jednostkowe panelu
```

Mockowane testy UI (Playwright) i testy na żywym API: [apps/web/tests/README.md](apps/web/tests/README.md).
LLM, HTTP i wyszukiwarka są w testach podmienione – testy nie wykonują płatnych wywołań.

## Produkcja

`docker-compose.prod.yml` (nie łączyć z `docker-compose.yml`): php-fpm za nginx, queue, scheduler, Redis z AOF,
PostgreSQL bez publikowanego portu, panel. API i panel są bindowane na `127.0.0.1` (`API_BIND`, `WEB_BIND`) –
publiczny ruch przez reverse proxy z TLS.

```bash
make deploy-init        # pierwszy raz: clone do PROD_DIR (domyślnie /srv/content-engine), potem deploy
make deploy             # na serwerze: git reset --hard origin/$BRANCH, build, migracja, up
make logs-prod / ps-prod / migrate-prod / create-user-prod / set-budget-prod / seed-prod
```
