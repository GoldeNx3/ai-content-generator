# Kontrola liczb, ręczne grupy tematów, monitoring – projekt

## Po co

- Wyłapać liczby, daty i ceny w artykule, których nie ma w faktach ani źródłach (literówki, zmyślenia) – bez kosztu AI.
- Dać redaktorowi darmową korektę pomyłek grupowania tematów.
- Dowiedzieć się o awarii kolejki na produkcji, zanim zauważy ją redaktor.

Warunek: płatne przebiegi tylko jako kroki na stronie tematu – żadna z tych funkcji nie dodaje płatnego wywołania.

## 1. Kontrola liczb (QA, krok 5, bez AI)

- Python `app/services/qa/numbers.py`: wyciąga z artykułu (lead, treść, bez bloków kodu, linków i cytatów `>`)
  liczby z kontekstem: kwoty (`10 USD`, `$10`, `49 zł`), procenty, liczby z jednostkami, liczby ≥ 10 i daty
  (`15 listopada 2026`, `2026-11-15`). Normalizuje zapis (`1 000`, `1,5`, `1.5`, `1,5 mln`).
- Liczba jest potwierdzona, gdy występuje (po normalizacji) w twierdzeniu faktu, treści źródła, tytule tematu
  albo „Naszym zdaniu”. Pomijane: rok bieżący i poprzedni, numery wersji (`Laravel 13`, `v2.1`, `GPT-5`),
  liczebniki w nagłówkach list (`3 sposoby`).
- Niepotwierdzona → issue `unverified_number` (severity `warning`, auto_fixable – Auto Fix usuwa lub zastępuje
  wartością z faktów), excerpt = zdanie z liczbą. Jedno issue na zdanie, najwyżej 10.
- Laravel: `FixPolicy` dopuszcza typ; panel QA: etykieta „Liczba bez potwierdzenia w źródłach”.

## 2. Ręczne grupy tematów (darmowe)

- „Odłącz od grupy”: `POST candidates/{id}/ungroup` – temat-duplikat staje się samodzielny (`topic_group_id`
  = null), zachowuje przejętą ocenę, uzasadnienie dostaje dopisek; temat główny nie może się odłączyć (nie ma od
  czego). Pełną własną ocenę daje istniejące „Oceń mimo to osobno · płatne”.
- „Połącz z tematem”: krok 2 pokazuje do 5 najbliższych tematów (ten sam workspace, podobieństwo embeddingu bez
  progu, `GET candidates/{id}/similar`) z przyciskiem „To ten sam temat”: `POST candidates/{id}/group
  {primary_id}` – temat dołącza do grupy wskazanego (jego główny temat, gdy wskazany jest duplikatem), przejmuje
  ocenę. Nie wolno: łączyć z samym sobą, z innym kontem, łączyć tematu, który sam ma członków (najpierw ich
  odłącz → 409).

## 3. Monitoring kolejki (webhook)

- `ALERT_WEBHOOK_URL` (Slack/Discord incoming webhook; puste = wyłączone), komenda `pipeline:health` w schedulerze
  co minutę. Sprawdza:
  - **worker nie odbiera zadań:** zadanie `queued` z `available_at` starszym niż 5 min (`ALERT_QUEUE_STALL_MINUTES`);
  - **zawieszone zadanie:** `running` dłużej niż 30 min (`ALERT_RUNNING_MINUTES`);
  - **seria błędów dostawcy:** ≥ 5 prób zakończonych 429/5xx/timeout w ostatnich 15 min (`ALERT_ERROR_BURST`).
- Wiadomość po polsku (rodzaj problemu, liczby, link do `/queue` z `FRONTEND_URL`); ten sam problem wysyłany
  najwyżej raz na 60 min (stan w cache), wiadomość „wróciło do normy” po ustąpieniu. Błąd webhooka tylko w logu.
- Format: JSON `{"text": ...}` (Slack) i `{"content": ...}` (Discord) – wybór po hoście URL-a.
- Działa systemowo (wszystkie workspace’y), niezależnie od `AUTOMATION_ENABLED`.

## Poza zakresem

E-mail, zewnętrzny endpoint statusu, ręczne przenoszenie członków między grupami jednym ruchem.
