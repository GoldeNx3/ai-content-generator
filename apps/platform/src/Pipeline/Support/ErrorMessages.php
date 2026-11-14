<?php

namespace Modules\Pipeline\Support;

final class ErrorMessages
{
    private const MESSAGES = [
        'llm_http_400' => 'OpenAI odrzucił zapytanie (HTTP 400). Najczęściej skonfigurowany model nie obsługuje użytych parametrów albo treść jest zbyt długa. Sprawdź nazwę modelu w .env.',
        'llm_http_401' => 'OpenAI odrzucił klucz API (HTTP 401). Klucz OPENAI_API_KEY jest nieprawidłowy, wygasł lub został unieważniony. Popraw go w .env, zrestartuj worker i ponów zadanie.',
        'llm_http_403' => 'Brak dostępu do OpenAI (HTTP 403). Konto lub projekt nie ma uprawnień do skonfigurowanego modelu albo region jest nieobsługiwany. Sprawdź uprawnienia projektu w panelu OpenAI.',
        'llm_http_404' => 'OpenAI nie zna skonfigurowanego modelu (HTTP 404). Sprawdź nazwę modelu w .env i dostęp projektu do tego modelu.',
        'llm_http_429' => 'Przekroczono limit OpenAI (HTTP 429): zbyt wiele zapytań albo brak środków na koncie. Zadanie ponowi się automatycznie; jeśli błąd wraca, sprawdź limity i saldo w panelu OpenAI.',
        'llm_connection' => 'Brak połączenia z OpenAI (sieć, DNS lub limit czasu). Zadanie ponowi się automatycznie; jeśli błąd wraca, sprawdź połączenie serwera z internetem.',
        'llm_not_configured' => 'OpenAI nie jest skonfigurowany: brakuje OPENAI_API_KEY. Dodaj klucz w .env, zrestartuj worker i ponów zadanie.',
        'invalid_output' => 'Model zwrócił odpowiedź w nieoczekiwanym formacie. Ponów zadanie; jeśli błąd się powtarza, rozważ inny model.',
        'refusal' => 'Model odmówił odpowiedzi albo zwrócił pustą odpowiedź. Sprawdź treść tematu i ponów zadanie.',
        'llm_error' => 'Błąd dostawcy LLM. Ponów zadanie; jeśli błąd wraca, sprawdź logi workera.',
        'timeout' => 'Zadanie przekroczyło limit czasu. Ponów je; jeśli błąd wraca, sprawdź obciążenie workera.',
        'execution_failed' => 'Nieoczekiwany błąd podczas wykonywania zadania. Szczegóły są w logach workera (docker compose logs queue).',
        'ai_process_failed' => 'Proces AI (Python) zakończył się błędem. Zadanie ponowi się automatycznie; szczegóły są w logach workera.',
        'worker_interrupted' => 'Praca została przerwana; poprzednie wywołanie mogło naliczyć koszt.',
        'cancelled' => 'Anulowano przez użytkownika.',
        'worker_lost' => 'Worker został przerwany; poprzednie wywołanie mogło naliczyć koszt.',
        'no_source_content' => 'Nie udało się pobrać treści żadnego źródła. Dodaj dostępne źródło ręcznie i ponów analizę lub skonfiguruj wyszukiwarkę.',
        'wordpress_not_configured' => 'WordPress nie jest połączony z tym workspace\'em. Połącz stronę w Ustawieniach.',
        'wordpress_invalid_url' => 'Adres WordPressa jest nieprawidłowy. Popraw połączenie w Ustawieniach.',
        'wordpress_timeout' => 'WordPress nie odpowiedział na czas. Zadanie ponowi się automatycznie.',
        'wordpress_connection' => 'Brak połączenia z WordPressem. Sprawdź, czy strona działa; zadanie ponowi się automatycznie.',
        'wordpress_invalid_json' => 'WordPress zwrócił nieprawidłową odpowiedź. Sprawdź, czy REST API działa i czy żadna wtyczka nie zmienia odpowiedzi.',
        'wordpress_http_401' => 'WordPress odrzucił dane logowania (HTTP 401). Połącz stronę ponownie w Ustawieniach.',
        'wordpress_http_403' => 'Użytkownik WordPressa nie ma uprawnień do tej operacji (HTTP 403).',
        'wordpress_http_404' => 'WordPress nie znalazł zasobu (HTTP 404). Wpis mógł zostać usunięty albo wtyczka Content Engine Bridge jest wyłączona.',
        'wordpress_http_429' => 'WordPress ogranicza liczbę zapytań (HTTP 429). Zadanie ponowi się automatycznie.',
        'wordpress_conflict' => 'WordPress zawiera inną treść. Sprawdź istniejący wpis i potwierdź nadpisanie w sekcji WordPress.',
        'wordpress_bridge_required' => 'Brak wtyczki Content Engine Bridge w WordPressie. Zainstaluj i włącz wtyczkę.',
        'wordpress_seo_plugin_mismatch' => 'Wtyczka SEO w WordPressie nie zgadza się z połączeniem (Yoast / Rank Math). Sprawdź połączenie w Ustawieniach.',
        'wordpress_publish_forbidden' => 'Użytkownik WordPressa nie może publikować ani planować wpisów. Zapisz jako szkic albo nadaj uprawnienia.',
        'wordpress_permalink_missing' => 'WordPress nie zwrócił adresu wpisu. Sprawdź ustawienia bezpośrednich odnośników.',
        'wordpress_schedule_elapsed' => 'Zaplanowany termin publikacji już minął. Wybierz nową datę.',
        'wordpress_schedule_changed' => 'Status wpisu w WordPressie zmienił się od zaplanowania. Sprawdź wpis i ponów.',
        'wordpress_verification_failed' => 'Nie udało się potwierdzić zapisu w WordPressie. Sprawdź wpis i ponów zadanie.',
    ];

    public static function for(?string $code): string
    {
        if ($code === null || $code === '') {
            return 'Nie udało się wykonać zadania.';
        }
        if (isset(self::MESSAGES[$code])) {
            return self::MESSAGES[$code];
        }
        if (preg_match('/^(llm|wordpress)_http_(\d{3})$/', $code, $match)) {
            $service = $match[1] === 'llm' ? 'OpenAI' : 'WordPress';
            $status = (int) $match[2];

            return $status >= 500
                ? "{$service} ma chwilowe problemy (HTTP {$status}). Zadanie ponowi się automatycznie; jeśli błąd wraca, spróbuj później."
                : "{$service} odrzucił zapytanie (HTTP {$status}). Sprawdź konfigurację i logi workera.";
        }

        return "Nie udało się wykonać zadania (kod: {$code}). Szczegóły są w logach workera.";
    }
}
