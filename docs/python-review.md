# Review backendu Python — 2026-10-03

Przegląd objął podział serwisów, kontrakty dostawców LLM, cykl życia researchu,
walidację danych, zapis w bazie oraz testy tych ścieżek. Refaktoryzacja zachowuje
endpointy, granice transakcji i dotychczasowe publiczne importy.

## Poprawione miejsca

| Problem | Zmiana | Dlaczego pomaga |
|---|---|---|
| `ResearchService` miała 349 linii i kilka odpowiedzialności | `ResearchService`, `ResearchPipeline`, `ResearchSourceLoader` w osobnych plikach | Status raportu, analiza i pobranie strony można czytać niezależnie. |
| `OpenAIProvider` łączył classify, research i write | Osobne `llm/classify.py`, `llm/research.py`, `llm/write.py` | Zmiana jednego etapu nie wymaga śledzenia pozostałych. |
| Każda fabryka tworzyła dostawcę wszystkich etapów | Fabryki tworzą właściwego dostawcę i wspólny klient HTTP | Zależności danego serwisu odpowiadają temu, co faktycznie robi. |
| Znacznik skrócenia przekraczał limit researchu | Miejsce na znacznik jest rezerwowane wewnątrz limitu | Prompt respektuje limit pojedynczego tekstu i sumy dokumentów. |

Nowe pliki mają polskie objaśnienia. `research_service.py` i
`article_service.py` są modułami zgodności; implementacje są odpowiednio w
`research/research.py` i `article/write.py`. `OpenAIProvider` deleguje do nowych
klas, aby istniejący kod nie wymagał natychmiastowej zmiany konstruktora.

Wszystkie klasy mieszczą się w 300 liniach, również po uwzględnieniu komentarzy
wewnątrz deklaracji. Nie dzielimy klas przez przypadkowe mixiny — pomocnicze
obiekty mają jasno określoną odpowiedzialność i jawne argumenty.

## Ryzyka pozostające po przeglądzie

Te miejsca wymagają osobnych zmian zachowania i testów, wykraczających poza
podział klas. Nie są naprawione przez samą refaktoryzację.

1. **Równoczesne generowanie artykułu:**
   [`ArticleService._next_version`](../apps/api/app/services/article/write.py)
   wylicza `MAX(version) + 1` bez blokady rekordu kandydata. Dwa żądania mogą
   wybrać tę samą wersję, a jedno polegnie na ograniczeniu unikalności przy
   zapisie. Zalecenie: serializować przydzielenie wersji i zmianę `is_current`
   w jednej transakcji, z testem dwóch niezależnych sesji.
2. **Równoczesny start researchu:**
   [`ResearchService.start`](../apps/api/app/services/research/research.py)
   sprawdza status, a potem go zapisuje. Dwa żądania mogą odczytać ten sam
   poprzedni status; sprawdzenie w Pythonie nie jest blokadą bazy. Zalecenie:
   atomowa zmiana statusu lub blokada rekordu oraz test konkurencyjnych startów.
3. **Pobieranie dowolnych URL-i:**
   [`ContentExtractor._download`](../apps/api/app/services/research/content_extractor.py)
   i fetcher RSS wykonują żądania pod podane adresy, także z przekierowaniami.
   Walidacja `HttpUrl` sprawdza format, lecz nie wyklucza localhost i sieci
   prywatnych. Przy dostępie niezaufanych użytkowników pozwala to skierować
   serwer do usług wewnętrznych (SSRF). Zalecenie: wspólna kontrola adresów
   docelowych, także po rozwiązaniu DNS i przy każdym przekierowaniu, oraz
   testy blokowania adresów wewnętrznych.

## Weryfikacja

- Pełny zestaw testów backendu: `docker compose exec -T api pytest -q`.
- Nowe testy granic budżetu: `tests/test_content_budget.py`.
- Testy wyboru modeli i tokenów dla etapów: `tests/test_llm_steps.py`.
- Kontrola składni wszystkich plików oraz długości każdej klasy przez AST.
- `git diff --check` i sprawdzenie lokalnych odnośników w dokumentacji.

Testy LLM i HTTP korzystają z lokalnych transportów, bez płatnych wywołań.
Testy bazy używają konfiguracji `TEST_DATABASE_URL`.
