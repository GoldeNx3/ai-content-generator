# Platforma Laravel + silnik AI w Pythonie

## Podział odpowiedzialności

**Laravel 13 (`apps/platform`)** – cała aplikacja poza obliczeniami AI:
- auth (Sanctum SPA, standardowe hashe), workspace'y, izolacja danych, budżety AI;
- źródła RSS (pobieranie i parsowanie – SimplePie), kandydaci, statystyki;
- trwały stan pipeline'u: research, wersje artykułów, QA, Auto Fix, akceptacja, publikacje WP;
- kolejka (Redis), worker (`queue:work`) i scheduler (`schedule:work`): orkiestrują kroki i uruchamiają Pythona;
- WordPress: połączenie (autoryzacja aplikacji WP, szyfrowanie `Crypt`), HTTP do WP + Content Engine Bridge;
- REST API dla Next.js (te same ścieżki i kształty JSON co wcześniejsze API w Pythonie).

**Python (`apps/api/ai`)** – bezstanowe obliczenia: `python -m ai <zadanie>`, JSON na stdin, JSON na stdout.
Brak bazy, HTTP serwera i kolejki. Każde zadanie zwraca wynik i listę wywołań LLM (`calls`: model, tokeny,
koszt wyliczony z cennika przekazanego na wejściu).

**Next.js (`apps/web`)** – bez zmian poza adresem API (Laravel) i logowaniem przez Sanctum (`/sanctum/csrf-cookie`).

## Zasady kodu (Laravel)

- Moduły: `src/<Moduł>/{Http/Controllers,Http/Requests,Data,Services,Queries,Commands,Models,Jobs,Enums,Exceptions,Console}`; namespace `Modules\<Moduł>`.
- Kontrolery invokable (jedna akcja), chude: walidacja w `Data` (laravel-data, atrybuty), logika w serwisie.
- Serwisy: zwykłe klasy, kilka metod, SOLID/DRY.
- `Queries\*Query::execute()` – odczyty z bazy; `Commands\*Command::execute()` – zapisy. Tylko operacje bazodanowe.
- Routing: atrybuty (`spatie/laravel-route-attributes`) na kontrolerach.
- Testy PHPUnit (Feature + Unit) do wszystkiego; bez komentarzy w kodzie, chyba że konieczne.

## Kontrakt zadań AI (stdin → stdout)

Wejście: `{"task": "...", "settings": {...modele, limity, cennik...}, "demo": bool, "input": {...}}`.
Wyjście sukcesu: `{"ok": true, "result": {...}, "calls": [{"stage","model","input_tokens","output_tokens","estimated_cost_usd","response_id"}]}`.
Wyjście błędu: `{"ok": false, "error": {"code","message","retryable","retry_after"}, "calls": [...]}` (kod wyjścia 0;
kod ≠ 0 tylko przy awarii interpretera – Laravel traktuje go jako błąd ponawialny).

| Zadanie | Wejście | Wynik |
|---|---|---|
| `classify` | kandydat | oceny, kategoria, uzasadnienie, `total_score` |
| `research.extract` | lista URL + domena oryginału | dla każdego: status pobrania, tytuł, wydawca, data, treść, typ i ocena źródła |
| `research.discover` | kandydat, treść oryginału, znane URL | zapytania, nowe źródła (już pobrane i ocenione) |
| `research.analyse` | kandydat, pobrane źródła | podsumowanie, fakty z `source_ids`, niepewności, konflikty, korekty typów źródeł |
| `article.brief` | kandydat, snapshot researchu, opcje, ostatnie struktury | kontekst + brief |
| `article.write` | kontekst + brief | treść, sekcje, SEO, ostrzeżenia, statystyki |
| `qa.evaluate` | wersja artykułu + snapshot | wyniki, problemy, `qa_passed` |
| `autofix.fix` | wersja, wybrane problemy QA | nowa treść, zmiany, fixed/skipped |
| `seo.prepare` | wersja, profil | uzupełniony profil SEO |
| `wordpress.render` | wersja, profil, wtyczka SEO | HTML, payload posta, meta SEO, hash treści |

Każdy krok jest osobnym wywołaniem; Laravel zapisuje wynik przed następnym krokiem, więc ponowienie nie płaci
ponownie za ukończone kroki (np. brief).

## Kolejka

- Tabela `pipeline_jobs` (UUID, kind, status `queued/running/retrying/succeeded/failed`, stage, próby, wynik, błąd)
  + `pipeline_job_attempts` (wywołania LLM z kosztami) – źródło stanu dla UI i budżetu.
- Laravel queue (Redis) wykonuje `RunPipelineJob`; jeden aktywny job na kandydata (częściowy indeks unikalny),
  `Idempotency-Key` → ten sam job, inne wejście → 409.
- Ponowienia: błędy `retryable` (429/5xx/timeout/połączenie) do `max_attempts` z backoffem; pozostałe → `failed`.
- Scheduler: pobieranie RSS + automatyczna klasyfikacja per workspace (budżet), sprzątanie.
