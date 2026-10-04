# Trwałe zadania — plan wdrożenia

Cel: wdrożyć zatwierdzony projekt `../specs/2026-10-03-durable-jobs-design.md`.
Wykonanie w tej sesji, z istniejącymi kontenerami do testów.

Wspólne kontrakty: Job/JobAttempt → JobRepository → JobExecution → handlery
classify/research/write → Worker. API używa JobService do enqueue, frontend
odczytuje JobRead. Wszyscy używają tych samych statusów i UUID.

- [x] 1. Testy enqueue/dzierżawy; modele, migracja i repozytorium kolejki.
- [x] 2. Testy fencing i atomowej publikacji; JobExecution, retry i checkpointy.
- [x] 3. Testy trzech handlerów; integracja serwisów i śledzenie wywołań LLM.
- [x] 4. Testy API 202/idempotency/status; przełączenie endpointów i ochrona wejścia.
- [x] 5. Worker, sygnały, timeout, heartbeat, recovery, scheduler i Compose.
- [x] 6. Panel: odczyt aktywnego zadania po wejściu, polling i historia prób.
- [x] 7. Migracja, pełne testy, build/lint frontendu, kontrola klas i dokumentacja.

Ryzyka do sprawdzenia: dwa workery i osobne sesje; wygasły worker zapisujący
wynik; crash między wynikiem i statusem; retry z zachowanym briefem; zamknięta
przeglądarka i restart API. Brak płatnych żądań w testach.

Weryfikacja: 131 testów backendu; npm lint/test i produkcyjny build Docker
(Turbopack); test Chrome na localhost:3000 z całkowicie mockowanym API, w tym
odtworzenie researchu po reload, chwilowy błąd odczytu wyniku oraz zapis v1
podczas zakończenia v2. Migracja pustej bazy, downgrade/upgrade na bazie testowej,
alembic check; migracja działającej bazy zachowała 6 ukończonych raportów.
Największa klasa Pythona: 234 linie. Niezależny review: wszystkie zgłoszone
problemy poprawiono i potwierdzono testami, w tym wyścig dwóch żądań partii.
Usługi uruchomione; worker healthy. Testy nie wywoływały OpenAI.
