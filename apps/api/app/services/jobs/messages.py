# Rola pliku: Zrozumiałe komunikaty błędów zadań dla użytkownika, budowane z kodu błędu.
# Kod (np. llm_http_401) zostaje w error_code dla diagnostyki; tutaj mówimy, co się stało i co zrobić.

import re

# Prefiks dawnego, ogólnego komunikatu. Starsze wiersze w bazie zawierają tylko surowy kod.
LEGACY_PREFIX = 'Nie udało się wykonać zadania. '

MESSAGES = {
    # OpenAI
    'llm_http_400': 'OpenAI odrzucił zapytanie (HTTP 400). Najczęściej skonfigurowany model nie obsługuje '
                    'użytych parametrów albo treść jest zbyt długa. Sprawdź nazwę modelu w .env.',
    'llm_http_401': 'OpenAI odrzucił klucz API (HTTP 401). Klucz OPENAI_API_KEY jest nieprawidłowy, wygasł '
                    'lub został unieważniony. Popraw go w .env, zrestartuj worker i ponów zadanie.',
    'llm_http_403': 'Brak dostępu do OpenAI (HTTP 403). Konto lub projekt nie ma uprawnień do skonfigurowanego '
                    'modelu albo region jest nieobsługiwany. Sprawdź uprawnienia projektu w panelu OpenAI.',
    'llm_http_404': 'OpenAI nie zna skonfigurowanego modelu (HTTP 404). Sprawdź nazwę modelu w .env '
                    'i dostęp projektu do tego modelu.',
    'llm_http_429': 'Przekroczono limit OpenAI (HTTP 429): zbyt wiele zapytań albo brak środków na koncie. '
                    'Zadanie ponowi się automatycznie; jeśli błąd wraca, sprawdź limity i saldo w panelu OpenAI.',
    'llm_connection': 'Brak połączenia z OpenAI (sieć, DNS lub limit czasu). Zadanie ponowi się automatycznie; '
                      'jeśli błąd wraca, sprawdź połączenie serwera z internetem.',
    'llm_not_configured': 'OpenAI nie jest skonfigurowany: brakuje OPENAI_API_KEY. Dodaj klucz w .env, '
                          'zrestartuj worker i ponów zadanie.',
    'invalid_output': 'Model zwrócił odpowiedź w nieoczekiwanym formacie. Ponów zadanie; jeśli błąd się '
                      'powtarza, rozważ inny model.',
    'refusal': 'Model odmówił odpowiedzi albo zwrócił pustą odpowiedź. Sprawdź treść tematu i ponów zadanie.',
    'llm_error': 'Błąd dostawcy LLM. Ponów zadanie; jeśli błąd wraca, sprawdź logi workera.',
    # Kolejka i worker
    'timeout': 'Zadanie przekroczyło limit czasu. Ponów je; jeśli błąd wraca, sprawdź obciążenie workera.',
    'execution_failed': 'Nieoczekiwany błąd podczas wykonywania zadania. Szczegóły są w logach workera '
                        '(docker compose logs worker).',
    'worker_interrupted': 'Praca została przerwana; poprzednie wywołanie mogło naliczyć koszt.',
    'worker_lost': 'Worker został przerwany; poprzednie wywołanie mogło naliczyć koszt.',
    # Research
    'no_source_content': 'Nie udało się pobrać treści żadnego źródła. Dodaj dostępne źródło ręcznie '
                         'i ponów analizę lub skonfiguruj wyszukiwarkę.',
    # WordPress
    'wordpress_not_configured': 'WordPress nie jest skonfigurowany: brakuje użytkownika lub hasła aplikacji. '
                                'Uzupełnij WORDPRESS_USERNAME i WORDPRESS_APP_PASSWORD w .env.',
    'wordpress_invalid_url': 'Adres WordPressa w konfiguracji jest nieprawidłowy. Popraw WORDPRESS_URL w .env.',
    'wordpress_timeout': 'WordPress nie odpowiedział na czas. Zadanie ponowi się automatycznie.',
    'wordpress_connection': 'Brak połączenia z WordPressem. Sprawdź, czy strona działa; zadanie ponowi się '
                            'automatycznie.',
    'wordpress_invalid_json': 'WordPress zwrócił nieprawidłową odpowiedź. Sprawdź, czy REST API działa '
                              'i czy żadna wtyczka nie zmienia odpowiedzi.',
    'wordpress_http_401': 'WordPress odrzucił dane logowania (HTTP 401). Sprawdź użytkownika i hasło aplikacji w .env.',
    'wordpress_http_403': 'Użytkownik WordPressa nie ma uprawnień do tej operacji (HTTP 403).',
    'wordpress_http_404': 'WordPress nie znalazł zasobu (HTTP 404). Wpis mógł zostać usunięty albo wtyczka '
                          'Content Engine Bridge jest wyłączona.',
    'wordpress_http_429': 'WordPress ogranicza liczbę zapytań (HTTP 429). Zadanie ponowi się automatycznie.',
    'wordpress_conflict': 'WordPress zawiera inną treść. Sprawdź istniejący wpis i potwierdź nadpisanie '
                          'w sekcji WordPress.',
    'wordpress_bridge_required': 'Brak wtyczki Content Engine Bridge w WordPressie. Zainstaluj i włącz wtyczkę.',
    'wordpress_seo_plugin_mismatch': 'Wtyczka SEO w WordPressie nie zgadza się z konfiguracją (Yoast / Rank Math). '
                                     'Popraw ustawienie SEO w .env albo w WordPressie.',
    'wordpress_publish_forbidden': 'Użytkownik WordPressa nie może publikować ani planować wpisów. '
                                   'Zapisz jako szkic albo nadaj uprawnienia.',
    'wordpress_permalink_missing': 'WordPress nie zwrócił adresu wpisu. Sprawdź ustawienia bezpośrednich odnośników.',
    'wordpress_schedule_elapsed': 'Zaplanowany termin publikacji już minął. Wybierz nową datę.',
    'wordpress_schedule_changed': 'Status wpisu w WordPressie zmienił się od zaplanowania. Sprawdź wpis i ponów.',
    'wordpress_verification_failed': 'Nie udało się potwierdzić zapisu w WordPressie. Sprawdź wpis i ponów zadanie.',
}


def public_error_message(code: str | None) -> str:
    if not code:
        return 'Nie udało się wykonać zadania.'
    if code in MESSAGES:
        return MESSAGES[code]
    if match := re.fullmatch(r'(llm|wordpress)_http_(\d{3})', code):
        service = 'OpenAI' if match[1] == 'llm' else 'WordPress'
        status = int(match[2])
        if status >= 500:
            return (f'{service} ma chwilowe problemy (HTTP {status}). '
                    'Zadanie ponowi się automatycznie; jeśli błąd wraca, spróbuj później.')
        return f'{service} odrzucił zapytanie (HTTP {status}). Sprawdź konfigurację i logi workera.'
    return f'Nie udało się wykonać zadania (kod: {code}). Szczegóły są w logach workera.'


def readable_error_message(code: str | None, message: str | None) -> str | None:
    """Zastępuje dawny komunikat z samym kodem nowym opisem; pozostałe komunikaty zostają."""
    if code and (message is None or message.startswith(LEGACY_PREFIX)):
        return public_error_message(code)
    return message
