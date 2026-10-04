# Article QA

QA uruchamia się ręcznie z karty **QA / Fact Checker** w szczegółach tematu.
Brief i pisanie pozostają jednym istniejącym krokiem UI, dlatego QA jest piątą
kartą interfejsu i szóstym logicznym etapem pipeline'u.

## Konfiguracja

- `OPENAI_QA_MODEL`: model QA; pusty używa modelu researchu. Lokalnie ustawiono `gpt-4.1`.
- `QA_PASS_SCORE=85`: próg readiness, 0–100.
- `QA_TIMEOUT_SECONDS=300`: timeout wywołania LLM.
- `JOB_QA_ARTICLE_TIMEOUT_SECONDS=900`: timeout całego joba.

Model, próg i cennik są snapshotem ustawień z chwili enqueue. Zmiana konfiguracji
wpływa na nowe zlecenia. Nie ma nowego researchu, auto-fix ani publikacji.

## Kontrakty

- `POST /api/articles/{id}/qa`: `202 JobRead`, `Location: /api/jobs/{uuid}`.
- `GET /api/articles/{id}/qa`: najnowszy trwały raport tej wersji lub `404`.
- `POST /api/articles/{id}/qa/retry`: nowe zlecenie po błędzie terminalnym.
- Ogólne `/api/jobs/{uuid}/retry` obsługuje również `qa_article`.
- Używaj UUID `Idempotency-Key` dla jednego zamiaru uruchomienia; ponowienie
  po utraconej odpowiedzi zwraca ten sam job, również po zakończeniu.
- Aktywne zlecenie dla Candidate blokuje równoległe płatne zadania (`409` z `job_id`).

Raport zapisuje numer wersji, hash i pełny snapshot ocenianego wejścia. Używa
researchu z chwili napisania tej wersji, nawet po ponowieniu researchu. Ręczna
edycja treści/tytułu/SEO unieważnia `Article.qa_passed`; raport pozostaje historyczny
z `is_stale=true`. Status redakcyjny artykułu jest niezależny od QA.

Ogólna ocena to zaokrąglona suma ocen z wagami 40/20/15/15/10. Połówki są
zaokrąglane w górę. Critical ogranicza ocenę do 60; high unsupported_claim do 75.
Readiness wymaga ukończonego, aktualnego raportu, przekroczenia progu oraz zera
unsupported claims i critical issues.

Supported/unsupported liczymy z wykazu twierdzeń i końcowych findings,
łącząc issue z krótszym fragmentem tego samego twierdzenia w tej samej sekcji.
Nie liczymy powtórzonych kart jako nowych claims. Parafrazowany supported claim
bez dosłownego fragmentu artykułu jest pomijany w liczniku i logowany.
Nieprawidłowy fragment problemu faktycznego kończy QA błędem, zamiast przypisywać
artykułowi zmyślony cytat. Dodatkowe źródło może dostarczać samodzielnych dowodów
poza wskazanym faktem, np. drugą stronę konfliktu; nie jest automatycznie błędem.

Każdy job ma jeden raport; automatyczne retry korzysta z tego samego raportu i
checkpointu odpowiedzi. Ręczne retry ma nowy job/raport. Wygasły worker nie może
zapisać wyniku. Znane tokeny i koszt zachowujemy także po błędzie późniejszej
walidacji; nieznane koszty są prezentowane jako nieznane.

## Weryfikacja

Standardowo uruchom backend pytest, frontend `npm test`, `npm run lint`, TypeScript
oraz `npm run build` z `NODE_ENV=production`. Przeglądarkowe testy `test:ui` i
`test:queue` przechwytują API i nie wykonują płatnych operacji.

Opcjonalny płatny test rzeczywistego wykrywania błędów:

```bash
docker compose exec -T api python -m tests.qa_live_check 7
```

Test używa snapshotu istniejącego artykułu SvelteKit oraz syntetycznego,
niezapisywanego draftu z celowo dodanymi błędami. Nie zmienia żadnego artykułu.

### Wynik rzeczywistego przebiegu (2026-10-04)

Temat 255: ponowiony Research → Brief → Write → QA, nowy Article 7, wersja 3.
Raport QA 4: overall 99; fakty 100, źródła 100, styl 94, struktura 100, SEO 100.
46 supported, 0 unsupported, 0 warnings, 0 critical; `qa_passed=true`.
Model `gpt-4.1-2025-04-14`, 29277 input / 4991 output tokens; koszt $0.098482.
POST QA zwrócił 202 w około 0.06 s. Wynik powstał w osobnym workerze.

Ręcznie sprawdzono wcześniejsze findings względem snapshotu: opisany konflikt
`$app/environment` nie był pominięty, eksperymentalne funkcje nie miały w artykule
wymyślonej daty stabilizacji, a dodatkowe źródło dotyczyło drugiej strony konfliktu.
Naprawiono te false positives i błędne parafrazy w polach excerpt; raport końcowy
nie zawiera issues. Artykuł nie był automatycznie poprawiany.

Osobny rzeczywisty test negatywny wykrył wszystkie pięć błędnych twierdzeń:
47% bez benchmarku, zmyślony cytat przypisany osobie (critical), datę 2025 zamiast
2026, twierdzenie o starym API ignorujące rozbieżne materiały oraz niepotwierdzoną
datę stabilizacji. Wynik 39/100, 5 unsupported, 1 critical, readiness false.

Końcowa weryfikacja: 228 backend tests, frontend unit tests, lint, TypeScript,
produkcyjny build oraz oba browser checks. Testy obejmują też równoczesny enqueue,
same-key retry race, wygasłą ostatnią próbę i spóźniony odczyt starej wersji w UI.
