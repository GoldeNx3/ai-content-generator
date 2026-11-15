# Pętla zwrotna redaktora, odświeżanie wpisów, raport kosztów – projekt

## Po co

- Teksty mają z czasem coraz mniej wymagać ręcznych poprawek: system uczy się z poprawek i odrzuceń redaktora.
- Nowy news o temacie już opisanym na blogu ma dawać aktualizację starego wpisu zamiast duplikatu (SEO).
- Redaktor ma widzieć, ile kosztuje gotowy artykuł i który krok jest najdroższy.

Warunek użytkownika: **każdy płatny przebieg to osobny, widoczny krok na stronie tematu `/candidates/[id]`**.

## Decyzje użytkownika

- Reguły: **AI proponuje, redaktor akceptuje** – nic nie trafia do profilu bez zgody.
- Odświeżenie: **nowy szkic w WordPressie obok starego wpisu** (z linkiem do starego), bez nadpisywania.

## Podejścia (rozważone)

- Reguły z poziomu Ustawień (analiza wszystkich poprawek konta naraz) – odrzucone: zadania kolejki są per temat
  (`pipeline_jobs.candidate_id` NOT NULL, FK, blokada jednego aktywnego zadania), a płatny krok miał być na stronie
  tematu. **Wybrane:** analiza poprawek jednego tematu jako płatny krok na jego stronie; zaakceptowane reguły trafiają
  do profilu konta, więc działają dla wszystkich kolejnych tematów.
- Odświeżenie przez nadpisanie wpisu – odrzucone przez użytkownika (ryzyko publiczne).

## 1. Pętla zwrotna

- Dane (darmowe, już są): wersje artykułu (`generated_content` vs `content` przy `is_edited`), powód odrzucenia wersji.
- Nowy płatny job `learn_feedback` (JobKind, CHECK constraint, handler w module Workspaces lub nowym `Feedback`):
  wejście = tytuł, różnica tekstu AI → tekst po edycji redaktora (ostatnia edytowana wersja), powody odrzuceń
  wersji tego tematu, aktualny profil redakcyjny. Python: zadanie `feedback.suggest` → do 8 propozycji
  `{kind: style_rule | banned_phrase, text, why}`; nie powtarza reguł już w profilu.
- Tabela `editorial_suggestions` (workspace_id, candidate_id, job_id, kind, text, why, status
  pending/accepted/dismissed). Akceptacja dopisuje do profilu: `banned_phrases` albo nowe pole
  `style_rules` (≤ 30 × ≤ 200 znaków), edytowalne w karcie „Profil redakcyjny”.
- Pisarz, brief i QA dostają `style_rules` (pisarz: obowiązkowe zasady stylu; QA: naruszenie = `style_issue`).
- UI: w kroku artykułu sekcja „Wnioski z Twoich poprawek”: przycisk „Zaproponuj reguły · płatne” aktywny, gdy temat
  ma edytowaną wersję albo odrzuconą z powodem; lista propozycji z „Dodaj do profilu” / „Pomiń” (darmowe).

## 2. Odświeżanie starego wpisu

- Krok 2 zapisuje wynik `already_covered` na temacie: `candidates.covered_by` jsonb
  `{type: post|article, title, url?, post_id?, article_id?, similarity}` (dla artykułu – URL i post_id z publikacji,
  gdy istnieje). Strona tematu pokazuje „Ten temat jest już na blogu: …”.
- Krok 4: opcja „Napisz jako aktualizację wpisu” (gdy `covered_by` ma `post_id`). Przed płatnymi wywołaniami Laravel
  darmowo pobiera treść starego wpisu z WP (`wp/v2/posts/{id}?_fields=content,title,link`, limit znaków); brak
  dostępu = błąd wejścia przed płatnością. Brief i pisarz dostają `refresh_of {title, url, content}`: zachować aktualne
  informacje, poprawić nieaktualne, wyróżnić nowości, link do starego wpisu dozwolony.
- Wersja artykułu zapamiętuje `refresh_of` (title, url, post_id). Publikacja bez zmian: nowy szkic. Panel WordPress
  pokazuje „To aktualizacja wpisu … – po sprawdzeniu przenieś treść lub przekieruj stary adres”.

## 3. Raport kosztów (darmowy)

- `GET /api/usage/report?month=YYYY-MM` (bieżący domyślnie): suma kosztu per rodzaj zadania i per etap wywołania
  (osobno Tavily `searching_sources`, embedding), liczba zadań, liczba wywołań o nieznanym koszcie, liczba
  wygenerowanych artykułów i średni koszt tematu doprowadzonego do artykułu (suma kosztów zadań tematów, które mają
  artykuł / liczba takich tematów). Źródło: `pipeline_job_attempts.llm_calls` jak w `WorkspaceSpendQuery`.
- UI: karta „Koszty” w Ustawieniach przy karcie zużycia, wybór miesiąca.

## Poza zakresem

Nadpisywanie wpisów WP, automatyczne dopisywanie reguł, analiza wszystkich poprawek konta naraz, wykresy.

## Pozostawione wykonawcy

Nazwy klas, układ UI w obrębie istniejących komponentów, limity długości promptów (rozsądne, spójne z istniejącymi).
