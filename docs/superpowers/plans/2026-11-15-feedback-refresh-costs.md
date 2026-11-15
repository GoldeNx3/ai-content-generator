# Pętla zwrotna, odświeżanie wpisów, raport kosztów – plan

**Spec:** `docs/superpowers/specs/2026-11-15-feedback-refresh-costs-design.md`

Global: polskie UI/docs; Laravel bez komentarzy; Python `# Rola pliku:`; płatne przebiegi tylko jako kroki na stronie
tematu; TDD (RED → GREEN); jeden commit na zadanie; merge/push na prośbę.

## Task 1: Raport kosztów (darmowy)
- `Usage/Queries/CostReportQuery::execute(int $workspaceId, CarbonImmutable $from, CarbonImmutable $to): array` –
  sumy per `job.kind` i per `call->>'stage'`, liczba zadań, nieznane koszty; tematy z artykułem i ich łączny koszt.
- `Usage/Data/CostReportData`, `GET /api/usage/report?month=YYYY-MM` (walidacja formatu, domyślnie bieżący miesiąc UTC).
- Web: `components/settings/cost-report.tsx` w Ustawieniach, wybór miesiąca; `api.costReport(month)`; typy.
- Testy: `tests/Feature/Usage/CostReportTest.php` (sumy per krok, Tavily osobno, izolacja kont, zły miesiąc → 422,
  średni koszt tematu z artykułem); UI check w `wordpress-settings-ui-check.mjs` lub nowym.

## Task 2: Odświeżanie wpisów
- Migracja `candidates.covered_by jsonb null`, `articles.refresh_of jsonb null`.
- `ClassifyHandler`: zapis `covered_by` (post: url, post_id z `wordpress_posts`; artykuł: publikacja → url, post_id).
- `CandidateData.covered_by`; krok 2 pokazuje notkę.
- Write: opcja `refresh: true` (walidacja w danych zlecenia; wymaga `covered_by.post_id`, inaczej 422);
  `WriteHandler` pobiera treść wpisu z WP (darmowe, przed płatnymi wywołaniami) i przekazuje `refresh_of` do briefu;
  wersja zapisuje `refresh_of`.
- Python: `BriefInput.refresh_of`, `ArticleContext.refresh_of`, sekcja w promptach briefu/pisarza; link do starego wpisu
  dozwolony (dopisany do `allowed` linków).
- Web: opcja w oknie generowania, notka w kroku 2 i w panelu WordPress.
- Testy: Laravel (covered_by zapisany; refresh pobiera treść i przekazuje; brak post_id → 422; błąd WP → job failed
  bez płatnego wywołania), pytest (prompt zawiera starą treść, link do starego wpisu nie jest usuwany).

## Task 3: Wnioski z poprawek
- JobKind `learn_feedback` (CHECK constraint, `isPaid`), handler `Workspaces/Handlers/LearnFeedbackHandler`,
  `POST /api/candidates/{candidate}/feedback` (wymaga edytowanej wersji lub odrzucenia z powodem, inaczej 422).
- Tabela `editorial_suggestions`; `GET /api/candidates/{candidate}/suggestions`,
  `POST /api/suggestions/{suggestion}/accept|dismiss` (binding w workspace).
- Profil: pole `style_rules` (≤ 30 × ≤ 200), akceptacja dopisuje (bez duplikatów) do `style_rules`/`banned_phrases`.
- Python: zadanie `feedback.suggest` (LLM, structured output, ≤ 8 propozycji, demo), `style_rules` w promptach
  pisarza i QA.
- Web: sekcja „Wnioski z Twoich poprawek” w kroku artykułu, pole „Zasady stylu” w karcie profilu.
- Testy: Laravel (warunek wejścia, zapis propozycji, akceptacja do profilu, izolacja, binding), pytest (prompt,
  walidacja, style_rules w pisarzu/QA), UI check.
