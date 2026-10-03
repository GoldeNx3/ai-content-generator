# AI Content Engine — MVP

Automatycznie zbiera nowe wpisy ze źródeł RSS/Atom, deduplikuje je po URL, zapisuje jako
*candidates*, ocenia ich potencjał przez LLM (OpenAI) i pokazuje w panelu administracyjnym,
gdzie można je zatwierdzić (`approved`), odrzucić (`ignored`) lub cofnąć do `pending`.

```text
RSS feeds → Fetch → Normalize → Deduplicate → Save Candidate → LLM Classification → Score + Category → Admin Dashboard
```

## 1. Wymagania

- Docker + Docker Compose v2
- (opcjonalnie, do pracy poza Dockerem) Python 3.13+, Node.js 22+
- klucz OpenAI API — tylko do klasyfikacji (fetch działa bez niego)

## 2. Instalacja

```bash
git clone <repo> content-engine && cd content-engine
cp .env.example .env        # uzupełnij OPENAI_API_KEY
make up                     # build + start (db, api, web)
make seed                   # przykładowe źródła RSS
```

## 3. Plik `.env`

| Zmienna | Opis |
|---|---|
| `DATABASE_URL` | URL bazy (SQLAlchemy, sterownik `psycopg`) |
| `TEST_DATABASE_URL` | baza dla testów (`content_test`, tworzona automatycznie przy pierwszym starcie Postgresa) |
| `OPENAI_API_KEY` | klucz OpenAI; bez niego endpointy klasyfikacji zwracają `503` |
| `OPENAI_CLASSIFIER_MODEL` | model klasyfikatora; puste = `gpt-4.1-mini` |
| `NEXT_PUBLIC_API_URL` | adres API widziany z przeglądarki (wkompilowany w build frontendu) |
| `CORS_ORIGINS` | dozwolone originy frontendu, po przecinku |
| `FETCH_INTERVAL_MINUTES` | co ile minut API samo pobiera źródła i klasyfikuje nowe wpisy (`0` = wyłączone) |
| `FETCH_MAX_AGE_DAYS` | wpisy starsze niż N dni są pomijane przy fetchu (`0` = bez limitu); wpisy bez daty są zachowywane |
| `CLASSIFY_BATCH_LIMIT` | maks. liczba wpisów klasyfikowanych w jednym wywołaniu `classify-pending` (ochrona budżetu LLM) |

`.env` jest w `.gitignore` — nie commituj sekretów.

## 4. Docker

`docker compose up` uruchamia:

| Usługa | Adres |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (`content` / `content`) |

Komendy `make`:

```text
make up        # docker compose up -d --build
make down      # zatrzymanie
make migrate   # alembic upgrade head
make seed      # przykładowe źródła RSS (idempotentne)
make logs      # logi wszystkich usług
make test      # testy backendu (pytest w kontenerze api)
make fetch     # ręczny fetch wszystkich aktywnych źródeł
make classify  # klasyfikacja niesklasyfikowanych wpisów
```

Kod API jest montowany jako wolumen — po zmianach w Pythonie: `docker compose restart api`.
Frontend jest budowany produkcyjnie — po zmianach: `docker compose up -d --build web`.

## 5. Migracje

Kontener `api` wykonuje `alembic upgrade head` przy każdym starcie. Ręcznie:

```bash
make migrate
# nowa migracja po zmianie modeli:
docker compose exec api alembic revision --autogenerate -m "opis zmiany"
```

## 6. Seed

```bash
make seed
```

Dodaje (jeśli nie istnieją) źródła: OpenAI, Anthropic, Google AI, Hugging Face, GitHub.
Lista jest tylko w `apps/api/app/jobs/seed.py` — logika aplikacji nie zna konkretnych źródeł.
Niedziałający feed nie przerywa fetchu pozostałych (błąd jest logowany i liczony w `errors`).

## 7. Uruchomienie i typowy flow

1. `make up && make seed`
2. Otwórz http://localhost:3000 → **Fetch all** → pojawiają się nowe wpisy (`pending`, bez score).
3. **Classify pending** (lub ikona ✨ w wierszu / **Classify** w szczegółach) → score 0–100, kategoria, uzasadnienie.
4. Approve / Ignore w tabeli lub w szczegółach wpisu.

Ponowny fetch nie tworzy duplikatów (`external_url` jest `UNIQUE`, a serwis odfiltrowuje istniejące URL-e).

## 8. Konfiguracja OpenAI

```env
OPENAI_API_KEY=sk-...
OPENAI_CLASSIFIER_MODEL=gpt-4.1-mini
```

Po zmianie: `docker compose up -d api` (env jest czytany przy starcie).
Klasyfikator używa Structured Outputs (`responses.parse` + model Pydantic `CandidateClassification`),
więc odpowiedź jest walidowana (score 0–100, kategoria z enumu) bez ręcznego parsowania JSON.
`total_score` liczy backend:

```text
total_score = round(relevance*0.40 + freshness*0.20 + search_potential*0.25 + commercial_potential*0.15)
```

Błąd LLM nie nadpisuje istniejących danych wpisu; w batchu jest logowany i pomijany.

## 9. Dodanie źródła RSS

- Panel: **Sources** → formularz *Name* + *RSS URL* → **Add source**.
- API:

```bash
curl -X POST http://localhost:8000/api/sources \
  -H 'Content-Type: application/json' \
  -d '{"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"}'
```

Źródło można wyłączyć (`PATCH /api/sources/{id}` z `{"active": false}`) lub usunąć (usuwa też jego wpisy).

## 10. Ręczny fetch

```bash
curl -X POST http://localhost:8000/api/sources/fetch       # wszystkie aktywne
curl -X POST http://localhost:8000/api/sources/3/fetch     # jedno źródło
```

```json
{"sources_processed": 5, "items_found": 42, "new_candidates": 11, "duplicates": 31, "skipped_old": 0, "errors": 0}
```

Dodatkowo API co `FETCH_INTERVAL_MINUTES` samo pobiera źródła, a jeśli jest ustawiony
`OPENAI_API_KEY`, od razu klasyfikuje nowe wpisy (do `CLASSIFY_BATCH_LIMIT` na przebieg).

## 11. Architektura

```text
content-engine/
├── apps/api            FastAPI + SQLAlchemy 2 (async, psycopg) + Alembic
│   └── app/
│       ├── api/            routery HTTP (cienkie: walidacja, kody błędów)
│       ├── core/           config (pydantic-settings), DB, logging
│       ├── models/         Source, Candidate, enumy
│       ├── schemas/        modele Pydantic request/response + CandidateClassification
│       ├── repositories/   zapytania SQL (filtry, sortowanie, paginacja, insert ON CONFLICT)
│       ├── services/
│       │   ├── rss_fetcher.py           httpx + feedparser → FeedEntry (RSS 2.0 / Atom)
│       │   ├── ingestion_service.py     fetch → filtr wieku → dedup → zapis
│       │   ├── classification_service.py
│       │   ├── scoring.py               total_score (ważona średnia)
│       │   ├── llm/                     LLMProvider / ResearchLLMProvider, OpenAIProvider, prompty, koszty
│       │   ├── research/                ekstrakcja, search, scoring źródeł, walidacja faktów, ResearchService
│       │   └── article/                 typy artykułów, brief + writer, walidacja, składanie Markdown, wersje
│       ├── jobs/           scheduler (pętla asyncio w lifespan), seed
│       └── main.py
├── apps/web            Next.js (App Router, TS strict) + Tailwind + shadcn/ui
│   ├── app/                / (dashboard), /candidates/[id], /sources
│   ├── components/         tabela, badge score/status, filtry, formularz źródła
│   ├── lib/                klient API, formatowanie
│   └── types/              typy odpowiedzi API
├── docker/postgres     init.sql (baza testowa)
├── docker-compose.yml
└── Makefile
```

Zasady:

- Logika biznesowa w `services/` — niezależna od FastAPI (używana przez endpointy i scheduler).
- Podmiana LLM: nowa klasa z metodą `classify_candidate(CandidateInput) -> CandidateClassification`
  i zmiana `services/llm/factory.py`. Zmiana modelu OpenAI — tylko `.env`.
- Brak kolejek: klasyfikacja batcha jest sekwencyjna; scheduler to jedna pętla asyncio w procesie API.
  Przy skalowaniu API do wielu instancji scheduler należy wydzielić (np. osobny proces/cron).

### REST API

```text
GET    /api/sources                 POST /api/sources
PATCH  /api/sources/{id}            DELETE /api/sources/{id}
POST   /api/sources/fetch           POST /api/sources/{id}/fetch

GET    /api/candidates              ?status&category&source_id&min_score&max_score
                                    &sort=total_score|created_at|original_published_at&order=desc|asc
                                    &page=1&page_size=25
GET    /api/candidates/{id}
POST   /api/candidates/{id}/classify
POST   /api/candidates/classify-pending   ?limit=
PATCH  /api/candidates/{id}/status  {"status": "approved" | "ignored" | "pending"}

GET    /api/stats                   karty dashboardu
GET    /health
```

## 12. Research Engine (etap 2)

Dla dowolnego wpisu: **Candidate → Start Research**. Raport zapisuje się w bazie (jeden aktualny research na wpis)
i jest pokazywany przy ponownym wejściu.

```text
Candidate → fetch original URL → extract article → LLM: search queries → SearchProvider
→ dedup URL, max 5 dodatkowych (najpierw najwyżej ocenione) → fetch + extract
→ LLM research (structured output) → walidacja URL-i → Facts ↔ Sources, uncertainties, conflicts
```

- **Ekstrakcja** (`services/research/content_extractor.py`): httpx (timeout, limit 5 MB, User-Agent aplikacji,
  błędy HTTP respektowane) → trafilatura → fallback BeautifulSoup (usuwa nav/header/footer/aside, cookie
  bannery, reklamy, komentarze, sekcje „related”). Zapisywany jest czysty tekst; surowy HTML (przycięty) trafia
  tylko do `raw_content` i nigdy do LLM ani do API.
- **Wyszukiwanie** (`services/research/search.py`): protokół `SearchProvider`. Domyślnie `ManualSearchProvider`
  (bez wyszukiwarki — dodatkowe źródła dodajesz ręcznie). `SEARCH_PROVIDER=tavily` + `TAVILY_API_KEY` włącza
  Tavily. Nowy dostawca (Brave, Serper, Google) = klasa z metodą `search()` + wpis w `get_search_provider()`.
  Zapytania generowane przez LLM są widoczne w panelu — przydają się do ręcznego szukania.
- **Scoring źródeł** (`services/research/source_scoring.py`): heurystyka backendu wg domeny
  (oficjalna strona/dokumentacja 100, oficjalne repo GitHub 95, gov/edu 95, Reuters/AP 90, media tech 80,
  blogi 65, społeczności 50, nieznane 40). Domena oficjalna = domena oryginalnego artykułu (o ile nie jest
  medium/społecznością). LLM może zasugerować typ tylko dla nierozpoznanych domen, z limitem score 65.
  Liczba źródeł nie jest traktowana jako dowód.
- **Fakty**: LLM może cytować wyłącznie URL-e z przekazanej listy. Po odpowiedzi backend sprawdza każdy URL
  względem `research_sources`; nieistniejące referencje są usuwane, a fakt bez żadnego poprawnego źródła
  trafia do *uncertainties* (nie jest zapisywany jako fakt).
- **Długość treści**: proste przycinanie na granicy akapitu — oryginał `RESEARCH_MAX_CHARS_ORIGINAL`,
  pozostałe `RESEARCH_MAX_CHARS_PER_SOURCE`, łącznie `RESEARCH_MAX_TOTAL_CHARS`.
- **Koszty**: każde wywołanie LLM zapisuje tokeny; `LLMCostCalculator` liczy `estimated_cost_usd` z cennika
  w konfiguracji (`LLM_PRICING` w `.env`, domyślne ceny w `app/core/config.py`). Nieznany model → koszt `null`.
- **Błędy**: niedziałający URL to źródło `failed` (z kodem HTTP), research idzie dalej. Błąd LLM lub brak
  jakiejkolwiek treści → research `failed`, ale pobrane źródła zostają. Bez `OPENAI_API_KEY` research pobiera
  i zapisuje źródła, a kończy się błędem „OPENAI_API_KEY is not set”.
- **Uruchamianie**: endpoint tworzy research (`running`) i wykonuje pipeline w tle (FastAPI `BackgroundTasks`,
  bez kolejki); panel odpytuje status co 2 s. Research przerwany restartem API jest oznaczany jako `failed`.

API:

```text
POST /api/candidates/{id}/research            nowy research (zachowuje ręcznie dodane źródła)   → 202
GET  /api/candidates/{id}/research            zapisany raport (404 jeśli brak)
POST /api/candidates/{id}/research/retry      ponowna analiza na istniejących źródłach           → 202
POST /api/candidates/{id}/research/sources    {"url": "..."} — fetch → extract → save            → 201
```

Ręczne źródło: dodaj URL w sekcji *Sources* raportu, potem **Re-run analysis**.

Zmienne `.env` etapu 2: `OPENAI_RESEARCH_MODEL` (puste = model klasyfikatora), `SEARCH_PROVIDER`,
`TAVILY_API_KEY`, `RESEARCH_MAX_EXTRA_SOURCES`, `RESEARCH_MAX_CHARS_*`, `LLM_PRICING`.

Uwaga: część serwisów (np. openai.com) blokuje boty (HTTP 403) — źródło zostaje oznaczone jako `failed`;
wtedy dodaj źródło alternatywne ręcznie. Playwright/Selenium celowo nie są używane na tym etapie.

## 13. Article Writer (etap 3)

Na ekranie wpisu, po ukończonym researchu: **Generate article** → modal (typ, długość, kąt, dodatkowe
instrukcje) → draft w sekcji *Article draft*. Bez researchu w statusie `completed` przycisk jest nieaktywny.

```text
Research (completed) → LLM: ArticleBrief → LLM: Writer (structured output) → walidacja backendu → Article (wersja N)
```

- **Źródło faktów**: writer dostaje wyłącznie brief + listę `FACT #id` (claim, confidence, źródła) + `SOURCE #id`
  + niepewności i konflikty. Podsumowanie researchu idzie tylko do briefu. Dodatkowe instrukcje są w prompcie
  oznaczone jako niezdolne do zmiany zasady „fakty tylko z researchu”.
- **Brief** (`ArticleBrief`, Pydantic): typ, kąt, odbiorcy, tytuł, key points, `required_facts`/`optional_facts`
  (ID faktów), niepewności do uniknięcia, konflikty, długość. Typ wybrany w modalu nadpisuje sugestię LLM,
  a długość ustala backend: zakres dla typu (news 600–1200, guide 1200–2500, comparison 1500–2500 …),
  ograniczony do ok. `150 + 45 × liczba faktów` słów (cel ±15%, nie limit) — mało faktów = krótszy tekst.
  Długość zależy głównie od researchu: research rozbija materiał na drobne fakty (jedna informacja = jeden fakt).
  Draft krótszy niż 60% celu dostaje ostrzeżenie.
- **Output writera**: `title, slug, lead, lead_fact_ids, sections[heading, content, used_fact_ids, source_ids],
  conclusion, conclusion_fact_ids, meta_title, meta_description`. Backend składa `content` (Markdown: `## H2`
  + akapity), liczy statystyki i normalizuje slug/meta.
- **Zabezpieczenia przed halucynacjami** (`services/article/validation.py`):
  - ID faktów spoza researchu są usuwane, ID źródeł spoza researchu (lub niepobranych) — też; każda sekcja
    dostaje dodatkowo źródła swoich faktów;
  - znaczniki `[FACT #8]` wstawione przez model do tekstu są usuwane (ID dołączane do referencji);
  - ostrzeżenia dla recenzenta: liczby nieobecne w żadnym fakcie, sekcje bez faktów, pominięte wymagane fakty,
    typowe dopiski bez pokrycia („ma na celu”, „co ma…”, „zgodność z regulacjami”…), za długi tytuł.
  To heurystyki, nie fact-checker — draft zawsze przechodzi przez Human Review.
- **Wersje**: każda generacja to nowy wiersz `articles` (`version` 1, 2, 3…); dokładnie jedna wersja ma
  `is_current` (częściowy indeks unikalny). Poprzednie drafty nie są usuwane. Ręczna edycja zmienia wersję
  w miejscu, ale `generated_content` zachowuje oryginał z LLM. Każda wersja ma `research_snapshot` (fakty
  i źródła z chwili generacji), więc historia jest czytelna także po ponownym researchu.
- **Koszt**: tokeny i koszt osobno dla briefu i writera (`brief_*`, `writer_*`), suma w `estimated_cost_usd`
  (`LLMCostCalculator`).
- **Modele**: `OPENAI_BRIEF_MODEL`, `OPENAI_WRITER_MODEL` (puste = model researchu → klasyfikatora).
  Generacja jest synchroniczna (ok. 10–60 s, timeout writera `WRITER_TIMEOUT_SECONDS`).

API:

```text
POST  /api/candidates/{id}/article       nowy draft (body opcjonalne: article_type, length, angle, instructions) → 201
GET   /api/candidates/{id}/articles      lista wersji (najnowsza pierwsza)
GET   /api/articles/{id}
POST  /api/articles/{id}/regenerate      nowa wersja; brakujące opcje z tej wersji → 201
PATCH /api/articles/{id}                 title, lead, content, meta_title, meta_description
PATCH /api/articles/{id}/status          draft | review | approved | rejected
```

Błędy: brak/nieukończony research → 409 „Complete research before generating an article.”, brak klucza → 503,
błąd LLM → 502 (nic nie jest zapisywane).

Jakość (obserwacje z prawdziwych generacji): gpt-4.1-mini poprawnie trzyma się liczb i faktów i ignoruje
instrukcje typu „dodaj ceny”, gdy cen nie ma w researchu, ale potrafi dopisywać ogólniki o celach/skutkach
i sklejać fakty nieprecyzyjnie. Ostrzeżenia wyłapują część takich miejsc; mocniejszy `OPENAI_WRITER_MODEL`
i redakcja ręczna pozostają zalecane.

## Testy

```bash
make test
```

Pokrywają: parser RSS/Atom (poprawny, uszkodzony feed, timeout, HTTP 500, brak daty/summary),
deduplikację i tworzenie wpisów, izolację błędów źródeł, filtr wieku, `total_score`, walidację
score, klasyfikację z mockowanym providerem (w tym błąd LLM w batchu), `OpenAIProvider` na
mockowanym transporcie HTTP oraz podstawowe endpointy. Research: ekstraktor (poprawna strona, pusty HTML,
404, timeout, fallback BeautifulSoup), pełny research, niedziałające źródło, duplikaty URL, limit i kolejność
źródeł, błąd LLM, walidacja URL-i faktów, confidence 0–100, relacje fakt ↔ źródło, koszty, endpointy.
Writer: brief (poprawny, brak researchu, research failed, walidacja structured output), draft, błąd LLM,
nieistniejące ID faktów i źródeł (także źródło niepobrane), liczby bez pokrycia, wersjonowanie, edycja, status, endpointy.
HTTP, SearchProvider i LLM są mockowane — testy nie wykonują płatnych ani sieciowych requestów.

## 14. Przewodnik po backendzie dla programisty znającego inne języki

Komentarze w plikach `.py` opisują rolę modułu i konstrukcje charakterystyczne dla
Pythona lub używanych bibliotek. Poniżej jest mapa, która pozwala czytać kod od
przepływu aplikacji, zamiast zaczynać od wszystkich szczegółów frameworków.

### Od czego zacząć czytanie

1. [`main.py`](apps/api/app/main.py) — odpowiednik bootstrapu aplikacji. `create_app()`
   tworzy FastAPI, dołącza routery i middleware. `lifespan()` wykonuje przygotowanie
   przy starcie i sprzątanie przy zamknięciu procesu.
2. [`api/router.py`](apps/api/app/api/router.py) i [`api/deps.py`](apps/api/app/api/deps.py)
   — rejestracja tras oraz składanie zależności. Tutaj widać, skąd endpoint dostaje
   sesję bazy, serwis i dostawcę LLM.
3. [`api/sources.py`](apps/api/app/api/sources.py) →
   [`ingestion_service.py`](apps/api/app/services/ingestion_service.py) →
   [`rss_fetcher.py`](apps/api/app/services/rss_fetcher.py) →
   [`candidate_repository.py`](apps/api/app/repositories/candidate_repository.py)
   — cały przykład przejścia od HTTP przez logikę biznesową do zapisu w bazie.
4. [`classification_service.py`](apps/api/app/services/classification_service.py)
   i [`llm/classify.py`](apps/api/app/services/llm/classify.py)
   — oddzielenie logiki klasyfikacji od konkretnego dostawcy modelu.
5. [`research.py`](apps/api/app/services/research/research.py)
   i [`write.py`](apps/api/app/services/article/write.py)
   — większe procesy, korzystające z tych samych zasad podziału odpowiedzialności.
6. [`tests/test_ingestion.py`](apps/api/tests/test_ingestion.py) — konkretne wejścia
   i oczekiwane rezultaty. Testy pomagają zrozumieć kontrakt serwisu.

### Składnia Pythona w tym projekcie

| Zapis | Jak go czytać |
|---|---|
| `def f(x: int) -> str:` | Deklaracja funkcji: argument `x` typu `int`, wynik typu `str`. |
| `self` | Jawny argument wskazujący instancję, podobny do `this`. Przy `obj.metoda()` Python przekazuje go automatycznie. |
| `__init__` | Inicjalizator instancji, w praktyce miejsce na przypisanie zależności i pól. |
| `str \| None` | Tekst albo brak wartości; `None` odpowiada idei `null`. |
| `list[T]`, `dict[K, V]`, `set[T]` | Lista, słownik klucz–wartość i zbiór unikalnych elementów. |
| `tuple[A, B]` | Krotka o dwóch elementach; np. `items, total = wynik` rozpakowuje wynik. |
| `@dekorator` | Funkcja przetwarzająca deklarowaną funkcję lub klasę, np. rejestrująca endpoint albo fixture. |
| `@property` | Metoda odczytywana jak pole, np. `candidate.source_name`. |
| `@staticmethod` / `@classmethod` | Metoda bez automatycznego `self` / metoda dostająca klasę jako `cls`. |
| `@dataclass(frozen=True, slots=True)` | Generuje m.in. inicjalizator; blokuje przypisania do pól i ogranicza zestaw atrybutów. Nie zamraża rekurencyjnie zawartości list. |
| `[x.id for x in items if x.active]` | List comprehension: filtr i mapowanie w jednym wyrażeniu, tworzące nową listę. |
| `{x.url for x in items}` | Set comprehension: analogiczna konstrukcja tworząca zbiór bez duplikatów. |
| `value or fallback` | Zwraca pierwszą wartość, jeśli jest truthy, inaczej drugą; `0`, `False`, pusty tekst i pusta kolekcja też uruchamiają fallback. |
| `x if warunek else y` | Wyrażenie warunkowe, odpowiednik operatora trójargumentowego. |
| `items[:limit]` | Slice: elementy od początku do `limit`, bez elementu pod tym indeksem. |
| `*args`, `**kwargs` | Zbieranie argumentów pozycyjnych/nazwanych; przy wywołaniu `f(*items)` i `f(**data)` oznacza rozpakowanie. |
| `f"ID={item.id}"` | Interpolacja wartości w tekście. |
| `with` / `async with` | Zarządzanie zasobem: wejście do kontekstu i sprzątanie także po wyjątku, podobnie do `using`/try-with-resources. |
| `raise X(...) from exc` | Rzucenie wyjątku z zachowaniem oryginalnej przyczyny. |
| `pass` / `...` | `pass` jest pustą instrukcją; `...` w metodach protokołów oznacza tu brak implementacji kontraktu. |

Wcięcia wyznaczają bloki kodu; nie ma klamer. `#` rozpoczyna komentarz.
Tekst w potrójnych cudzysłowach na początku modułu, klasy lub funkcji to **docstring**,
dostępny także przez introspekcję. Potrójne cudzysłowy w promptach oznaczają zwykły
wielowierszowy tekst, który aplikacja wysyła modelowi.

Adnotacje typów zwykle pomagają edytorowi i analizatorom, ale sam Python nie wymusza
ich przy każdym przypisaniu. W tym projekcie **Pydantic** sprawdza dane przy
budowaniu modeli, a **SQLAlchemy** wykorzystuje deklaracje do mapowania bazy.
`_nazwa` oznacza umownie element wewnętrzny; nie jest modyfikatorem dostępu.
Nazwy w `UPPER_CASE` oznaczają umownie stałe, bez blokady ich zmiany przez język.

### `async`, `await` i zadania w tle

Wywołanie `async def` tworzy korutynę. Dopiero `await` lub zaplanowanie jej jako
zadania uruchamia pracę. Podczas oczekiwania na asynchroniczną operację I/O pętla
zdarzeń może wykonywać inne zadania. `await` nie tworzy osobnego wątku i nie
przyspiesza automatycznie obliczeń CPU.

```python
# Najpierw czekamy na pobranie, potem wykorzystujemy wynik.
entries = await fetcher.fetch(source)
```

`asyncio.create_task(...)` w schedulerze planuje pracę współbieżną z obsługą API.
`asyncio.gather(...)` w researchu zbiera wyniki kilku korutyn. Pętla z `await` w
każdej iteracji jest natomiast sekwencyjna — tak działa klasyfikacja batcha.

`yield` w `lifespan()` rozdziela start od zamknięcia aplikacji. W zależności sesji
bazy przekazuje sesję do obsługi żądania, po czym wykonanie wraca do funkcji i
kontekst sesji jest zamykany. W fixtures pytest podobnie rozdziela przygotowanie
zasobów od sprzątania po teście.

Research używa FastAPI `BackgroundTasks`: endpoint zapisuje `running` i zwraca
`202`, a analiza odbywa się po odpowiedzi. Zadanie otwiera własną sesję bazy w
[`research/factory.py`](apps/api/app/services/research/factory.py). To ważne,
ponieważ sesja żądania ma osobny cykl życia. Te zadania nie są trwałą kolejką;
restart procesu przerywa ich wykonywanie.

### Trzy różne rodzaje modeli

| Miejsce | Odpowiedzialność | Przykład |
|---|---|---|
| `models/` — SQLAlchemy | Tabele, kolumny, klucze i relacje w bazie. | `Candidate` reprezentuje rekord `candidates`. |
| `schemas/` — Pydantic | Walidacja danych HTTP i Structured Outputs LLM. | `CandidateRead` opisuje odpowiedź API. |
| `services/llm/base.py` — dataclasses | Przekazywanie danych pomiędzy serwisami a dostawcą LLM. | `CandidateInput` zawiera dane do klasyfikacji. |

`Mapped[str] = mapped_column(...)` oznacza pole ORM, a nie zwykłe przypisanie
tekstu. `relationship(...)` pozwala przejść do powiązanych rekordów.
`lazy="joined"` ładuje relację razem z zapytaniem głównym; inne strategie
ładowania są dobierane w modelach i zapytaniach.

`BaseModel` Pydantic sprawdza pola. `Field(ge=0, le=100)` ogranicza wartość do
zakresu 0–100. `ConfigDict(from_attributes=True)` pozwala budować odpowiedź z
atrybutów obiektu ORM. `model_dump()` daje słownik, `model_validate()` waliduje
wejście, a `model_copy(update=...)` tworzy kopię ze zmianami — samo `update` w tej
metodzie nie wykonuje ponownej walidacji.

### Jak czytać zapis do bazy

```python
session.add(candidate)             # dołącz obiekt do sesji
await session.flush()             # wyślij zmiany; można otrzymać ID, bez commitu
await session.commit()            # zatwierdź transakcję
await session.refresh(candidate)  # odczytaj aktualne wartości z bazy
```

To przykład znaczenia operacji; nie każda ścieżka potrzebuje wszystkich czterech.
`rollback()` wycofuje bieżącą transakcję po błędzie. Wcześniej zatwierdzone dane
pozostają zapisane — dlatego research może zachować pobrane źródła, nawet jeśli
późniejsza analiza LLM się nie powiedzie.

`select(Model).where(...)` buduje opis zapytania SQL. Dopiero `await
session.execute(...)`, `scalar(...)` lub `scalars(...)` je wykonuje. `scalar`
zwraca pojedynczą wartość, a `scalars` pozwala odczytać wartości pierwszej kolumny
kolejnych wierszy, często obiekty ORM. `session.get(Model, id)` szuka po kluczu
głównym i może korzystać z obiektu już obecnego w sesji.

Zmiana klasy w `models/` sama nie aktualizuje działającej bazy. Do tego służą
migracje w `alembic/versions/`: `upgrade()` wprowadza zmianę schematu,
`downgrade()` opisuje jej cofnięcie. `alembic/env.py` ładuje metadane wszystkich
modeli, aby Alembic mógł porównać deklaracje z bazą.

### Przykład całego przepływu: pobranie RSS

1. Router `api/sources.py` odbiera żądanie pobrania źródeł.
2. `Depends` z `api/deps.py` dostarcza `IngestionService` z sesją i `RssFetcher`.
3. Fetcher pobiera HTTP, parsuje XML RSS/Atom i zwraca listę `FeedEntry`.
4. Serwis filtruje wiek wpisów i usuwa duplikaty z pobranego zestawu.
5. Repozytorium sprawdza istniejące URL-e i zapisuje nowe przez
   `INSERT ... ON CONFLICT DO NOTHING`; unikalność w bazie chroni także przed
   równoległymi zapisami tego samego adresu.
6. Serwis zatwierdza transakcję i zwraca `FetchResult` z licznikami.
7. FastAPI serializuje wynik do JSON, który odczytuje frontend.

Klasyfikacja jest kolejną operacją. Research buduje materiał i fakty ze źródeł,
a writer korzysta z tego researchu do utworzenia nowej wersji artykułu.
`Protocol` opisuje metody wymagane od dostawcy LLM lub wyszukiwarki, podobnie do
interfejsu. Zgodność jest strukturalna: klasa z odpowiednimi metodami nie musi
jawnie dziedziczyć po protokole.

### Jak czytać i uruchamiać testy

Funkcje `test_*` są scenariuszami, a `assert` opisuje oczekiwany wynik.
`pytest.raises(...)` sprawdza spodziewany wyjątek. `parametrize` powtarza scenariusz
dla wielu danych. Nazwy argumentów testu wskazują fixtures, które pytest ma
przygotować; wspólne fixtures są w `tests/conftest.py`.

`FakeProvider`, `FakeResearchLLM` i `FakeArticleLLM` zastępują prawdziwy LLM.
`httpx.MockTransport` udaje odpowiedzi zewnętrznych usług, a `ASGITransport`
wywołuje aplikację FastAPI w procesie testu, bez otwierania portu HTTP.
Testy integracyjne nadal potrzebują PostgreSQL; fixture tworzy tabele i czyści
dane w **bazie testowej** wskazanej przez `TEST_DATABASE_URL`.

```bash
make test
# Jeden plik testów w działającym kontenerze:
docker compose exec api pytest tests/test_ingestion.py -q
```

Pliki `__init__.py` oznaczają pakiety importowane np. jako `app.services`.
Większość służy wyłącznie organizacji katalogów; `models/__init__.py` dodatkowo
importuje modele, aby ich tabele zostały zarejestrowane w metadanych ORM.


## 15. Podział etapów po review Pythona

Każdy etap ma oddzielną logikę biznesową i własnego dostawcę LLM. Najłatwiej
czytać od serwisu, a szczegóły promptów i komunikacji z modelem sprawdzać dopiero
w drugiej kolumnie:

| Etap | Serwis: co robi aplikacja | Dostawca: jak rozmawia z LLM |
|---|---|---|
| `classify` | [`classification_service.py`](apps/api/app/services/classification_service.py) — zapis ocen, kategorii i kosztu | [`llm/classify.py`](apps/api/app/services/llm/classify.py) — prompt i schemat klasyfikacji |
| `research` | [`research/research.py`](apps/api/app/services/research/research.py) — rozpoczęcie, statusy, retry, ręczne źródła | [`llm/research.py`](apps/api/app/services/llm/research.py) — zapytania wyszukiwania i raport |
| `write` | [`article/write.py`](apps/api/app/services/article/write.py) — brief, draft, walidacja i wersje | [`llm/write.py`](apps/api/app/services/llm/write.py) — generacja briefu i tekstu |

Research składa się z trzech małych klas:

- `ResearchService` w `research.py` odpowiada za publiczne operacje i stan raportu.
- `ResearchPipeline` w [`pipeline.py`](apps/api/app/services/research/pipeline.py)
  wykonuje kolejne kroki analizy; w metodzie `run()` są ponumerowane objaśnienia.
- `ResearchSourceLoader` w [`source_loader.py`](apps/api/app/services/research/source_loader.py)
  pobiera stronę i wypełnia obiekt źródła. Nie robi commitu; moment trwałego
  zapisu wybiera serwis lub pipeline.

To **kompozycja**: serwis przechowuje obiekty pomocnicze w polach i wywołuje ich
metody, podobnie do delegowania w innych językach. Nie trzeba śledzić dodatkowej
hierarchii dziedziczenia ani mixinów z logiką biznesową.

Wspólny [`llm/client.py`](apps/api/app/services/llm/client.py) obsługuje HTTP,
parsowanie odpowiedzi, wyjątki i liczniki tokenów. Dostawcy etapów przekazują mu
model, prompt i typ oczekiwanego wyniku. [`llm/factory.py`](apps/api/app/services/llm/factory.py)
tworzy tylko dostawcę potrzebnego etapu. `OpenAIProvider` pozostaje adapterem
zgodności dla dotychczasowych integracji i deleguje do tych samych małych klas.

Dawne `research_service.py` i `article_service.py` eksportują klasy z nowych
plików. To most dla starszych importów, bez drugiej kopii logiki. Nowy kod
aplikacji używa już docelowych ścieżek.

Przy rozbudowie utrzymuj klasy do 300 linii, licząc także komentarze wewnątrz
klasy. Gdy klasa rośnie, wydziel pełną odpowiedzialność z jawnymi argumentami;
samo przenoszenie przypadkowych metod do drugiego pliku utrudnia czytanie.

Limit znaków researchu obejmuje również znacznik skrócenia tekstu. Regresję tego
zachowania sprawdza `tests/test_content_budget.py`; wybór modeli dla etapów
sprawdza `tests/test_llm_steps.py`. Podsumowanie ustaleń:
[review backendu](docs/python-review.md).
