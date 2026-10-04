# WordPress Publisher + SEO (etap 8)

Publikacja jest zadaniem kolejki, domyślnie tworzy **draft**. Wymaga zatwierdzonej wersji i aktualnego, zaliczonego QA. Schedule i Publish Now są jawnymi akcjami. Nowa zatwierdzona wersja nigdy nie nadpisuje WP automatycznie.

## Uruchomienie

1. Ustaw zmienne z `.env.example`. Credentials przechowuj wyłącznie w env/secret storage. `WORDPRESS_APP_PASSWORD` to Application Password, nie hasło logowania. Konto musi mieć uprawnienia do edycji wpisów, taksonomii i opcjonalnie mediów; publikowanie wymaga osobnego uprawnienia.
2. Zainstaluj i aktywuj `integrations/wordpress/content-engine-bridge` jako plugin WordPress. Bridge jest wymagany do trwałej idempotencji i ochrony przed konfliktami. Nie zmienia core WP. Jego tabele oraz wp_posts muszą używać InnoDB.
3. Uruchom migrację `alembic upgrade head` w kontenerze API. Przebuduj API/worker po zmianie requirements.
4. Dla lokalnego GoldenDEV: `docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.wordpress.yml up -d --build`. Publiczny URL: `http://localhost:8080/blog`; wewnętrzny API URL: `http://goldendev-wordpress-wordpress-1/blog`. Zewnętrzna sieć `goldendev-wordpress_default` musi istnieć. `WORDPRESS_INSTANCE_ID` musi być stabilny i unikalny dla tej instalacji silnika.
5. Sprawdź `POST /api/wordpress/test-connection`, następnie otwórz zatwierdzony artykuł → krok 4 → zakładka SEO, a po QA i approval → WordPress → Create Draft.

## Dane i bezpieczeństwo publikacji

Istniejący model `Article` jest wersją artykułu. `seo_title` używa istniejącego `meta_title`; pozostałe dane SEO znajdują się w `seo_data`. Nowe snapshoty QA obejmują SEO, stare snapshoty pozostają kompatybilne. Przygotowanie brakujących metadanych dla wcześniej zatwierdzonych wersji zapisuje profil publikacji, bez zmiany zatwierdzonej treści i bez nowego researchu. LLM korzysta wyłącznie z zamrożonych article/brief/research, zachowując istniejące niepuste pola.

Pełne SEO powstaje przy pisaniu w kroku 4 i jest dostępne w zakładce SEO przed QA. Osobny przycisk generowania SEO nie jest potrzebny w kroku WordPress. Endpoint prepare pozostaje wyłącznie dla zgodności starszych wersji.

Jedna `WordPressPublication` na candidate przechowuje ostatnią wysłaną wersję, post ID, permalink, status, media, profil, ostrzeżenia i hash treści WP. Nowa wersja wymaga ręcznego Sync. Canonical pochodzi z permalinku WP (również po rozstrzygnięciu kolizji slugów), nigdy ze źródeł researchu.

Bridge używa stabilnej tożsamości instance:candidate oraz kluczy operacji job:phase. Trwały rejestr operacji, transakcje i blokada tożsamości zapewniają odzyskanie po utracie odpowiedzi HTTP bez ponownego CREATE. Aktualizacje porównują hash surowej treści pod blokadą wiersza WP. Konflikt nie nadpisuje ręcznych zmian; UI wymaga jawnego potwierdzenia aktualnego hasha. Kontrola dotyczy treści, nie wszystkich ręcznych zmian taksonomii/metadanych.

Worker ponawia 429, 5xx, timeout i błędy połączenia. 401/403, brak approval/aktualnego QA i konflikt wymagają interwencji. Sekrety WP są wyłączone ze snapshotów jobs, odpowiedzi i logów. Timeout wynosi domyślnie 30 sekund. Test connection nie tworzy posta.

Schedule wymaga daty ze strefą czasową; aplikacja przechowuje UTC i wysyła date_gmt. Spóźnione, jeszcze niewysłane zadanie harmonogramu jest blokowane zamiast publikować natychmiast. Odzyskanie już zaakceptowanej operacji uwzględnia zmianę future → publish przez WP cron.

## SEO i treść

Adaptery Yoast, RankMath i none są wymienne. Bridge udostępnia pola przez register_post_meta/show_in_rest i deklaruje capabilities. Brak dostępnych pól powoduje ostrzeżenie, a nie utratę draftu. Niezgodność aktywnego pluginu z konfiguracją blokuje wysyłkę. Podstawowe schema/OG/canonical pozostają pod kontrolą aktywnego SEO pluginu; Bridge uzupełnia jego filtry zamiast emitować drugi zestaw. Przy none Bridge odpowiada za head; przed wdrożeniem sprawdź dodatkowe wtyczki i theme, które mogą samodzielnie generować SEO.

Markdown jest konwertowany do HTML z tabelami, listami i H2/H3; H1 jest zamieniany na H2. Źródła są opcjonalną sekcją, zwykłe linki zewnętrzne dostają noopener. Internal links są wstawiane wyłącznie po potwierdzeniu istniejącej, opublikowanej strony w tej instalacji WP. Kategorie ogranicza lista w UI; tagów jest maksymalnie 8. FAQ/HowTo wymaga rzeczywistych pytań/odpowiedzi lub kroków w treści.

Featured image jest opcjonalny. Upload mediów deduplikuje zawartość; lokalny asset musi znajdować się pod WORDPRESS_ASSET_ROOT. Zdalny obraz ma ograniczenia publicznego adresu, MIME i rozmiaru. Bez featured image plugin może użyć domyślnego obrazu witryny.

## API i weryfikacja

- POST `/api/article-versions/{id}/wordpress` — 202, status draft/future/publish.
- GET `/api/article-versions/{id}/wordpress` — profil, checks, publikacja, konflikt i nowsza zatwierdzona wersja.
- POST `.../wordpress/sync` — aktualizacja istniejącego posta, zachowuje aktualny status WP, o ile nie wybrano innego.
- POST `.../wordpress/prepare` — generowanie brakujących SEO w workerze.
- PATCH `.../wordpress/settings` — wybór kategorii, tagów, autora, schema i pozostałych danych.
- POST `/api/wordpress/test-connection` — users/me, posts oraz capabilities Bridge.

Po zapisie publisher pobiera post i sprawdza title, slug, raw HTML, status, category, tags, author, featured image i dostępne SEO metadata.

Testy: `docker compose exec -T api pytest -q`; frontend `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build -- --webpack`. Testy HTTP WP są mockowane. `tests/wordpress_bridge_live_check.py` uruchamiaj świadomie na lokalnym WP: tworzy testowy draft, sprawdza współbieżność/recovery/conflict i przenosi go do kosza. PHP `integrations/wordpress/tests/schema.php` sprawdza kontrakty filtrów schema.

RankMath ma adapter i testy kontraktowe; pełny test z aktywnym pluginem wykonano dla Yoast. Dla draftów Yoast nie emituje canonical w uwierzytelnionym preview, mimo zapisanego canonical meta. Publiczny permalink draftu nie jest publicznym artykułem. Globalne ustawienie WP „nie indeksuj” jest respektowane.

Ponowne wysłanie wpisu w koszu tworzy nowy draft i pozostawia poprzedni wpis w koszu. Po potwierdzonym trash lub 404 publisher usuwa lokalne powiązanie, a Bridge pod blokadą atomowo wycofuje nieaktualną mapę i tworzy nowy draft. Błędy uprawnień i sieci nie uruchamiają CREATE. Sync również obsługuje kosz i trwałe usunięcie.

UI sprawdza aktualny status WP przy wczytaniu i powrocie do okna; przycisk „Sprawdź stan WordPress” odświeża go ręcznie. Po trash/404 pokazuje „Wyślij ponownie jako draft”. Wybierz dowolną zatwierdzoną wersję z aktualnym QA — wysłana zostanie jej treść, nie poprzednia wersja zapamiętana w publication. Powiązanie nie jest kasowane przy samym odczycie. Dopiero jawne wysłanie tworzy nowy draft; retry tego zadania odzyskuje ten sam nowy post bez duplikatu.
