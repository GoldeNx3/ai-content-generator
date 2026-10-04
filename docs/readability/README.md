# Czytelność i SEO przy generowaniu

Reguły globalne są wspólne dla briefu, writera, QA i Auto Fix: `app/services/article/readability.py`. SEO powstaje razem z artykułem w kroku 4.

- Cel 150–250 słów między H2/H3; maksymalnie 300. H3 dzielą dłuższy temat bez skracania potrzebnych wyjaśnień.
- Akapity zwykle 40–100 słów, maksymalnie 150.
- Cel 30–40% zdań z naturalną relacją: również, ponadto, jednak, natomiast, z kolei, mimo to, ponieważ, dlatego, na przykład, najpierw, następnie, jeśli, podobnie. Spójnik nie może sugerować nieudowodnionej przyczynowości.
- Większość zdań do 20 słów; cel maksymalnie 25% dłuższych. Cytaty, nazwy i kod pozostają wierne źródłom.
- Strona czynna, gdy wykonawca jest znany; różnorodne początki zdań, brak monotonnych przejść i keyword stuffing.
- Naturalna fraza kluczowa w SEO title, leadzie, opisie i odpowiednim nagłówku; H1 pochodzi z WordPressa. Brak wymyślonych linków/obrazków/FAQ.

Backend niezależnie od LLM liczy widoczny tekst Markdown i zgłasza warning dla bloku ponad 300 słów oraz akapitu ponad 150. Fenced code nie jest oceniany jak proza, H3 w code fence nie dzieli sekcji; docelowe adresy linków nie są liczone jak tekst. Ostrzeżenia są widoczne po generowaniu oraz w trwałych issues QA (structure_issue/style_issue, auto_fixable). Nie zastępują faktograficznych kryteriów approval. Auto Fix wykonuje tylko wskazane poprawki i tworzy wersję wymagającą nowego QA.

Słowa łączące, zdania i strona bierna są oceniane kontekstowo przez model QA; aplikacja nie udaje dokładnego analizatora językowego Yoast ani nie podaje wymyślonego procentu. Docelowe ustawienia Yoast i jego obsługa języków mogą zmieniać progi. Zasady są celami redakcyjnymi, nie gwarancją wszystkich zielonych kontrolek. Szczególnie brak obrazu/linku nie uzasadnia ich wymyślania.

Źródła reguł: https://yoast.com/transition-words-why-and-how-to-use-them/ oraz https://github.com/Yoast/wordpress-seo/blob/trunk/packages/yoastseo/src/scoring/assessments/SCORING%20READABILITY.md . Dla standardowego tekstu rozkład nagłówków 300–350 słów bywa warning, a dla cornerstone progi są niższe; aplikacja przyjmuje wspólny limit 300 z celem poniżej 250.

Zmiana dotyczy nowych generacji oraz kolejnych uruchomień QA/Auto Fix. Istniejące zatwierdzone artykuły i treść w WordPressie nie są automatycznie przepisywane.

Weryfikacja 2026-10-04: 335 testów backendu passed, w tym 6 testów czytelności/integracji. Kontrola na istniejącym Article1 wskazała 363 słowa pod H2 „Reklamacja zamknięta, choć problem nadal trwał”, zgodnie ze zgłoszeniem użytkownika. API/worker zrestartowane po testach.

Naprawa walidacji QA: uwaga seo_issue, która zwraca połączone etykietowane pola (np. meta_title/meta_description/lead), jest normalizowana do jednego literalnego pola wyłącznie gdy każda wartość dokładnie odpowiada aktualnej wersji. Parafrazy, nieznane etykiety i zmyślone wartości nadal są odrzucane; reguła nie dotyczy factual issues. Prompt wymaga jednego excerpt bez etykiet. UI otrzymuje czytelny powód invalid_output zamiast samego kodu. Regresja: 339 testów passed.
