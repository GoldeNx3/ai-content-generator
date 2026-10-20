# Rola pliku: Komunikaty błędów zadań są zrozumiałe dla użytkownika, a nie surowym kodem.

import pytest

from app.services.jobs.messages import LEGACY_PREFIX, public_error_message, readable_error_message
from app.services.llm.base import LLMNotConfiguredError


def test_openai_401_explains_api_key():
    message = public_error_message('llm_http_401')
    assert 'OPENAI_API_KEY' in message and 'llm_http_401' not in message


@pytest.mark.parametrize('code,fragment', [
    ('llm_http_502', 'chwilowe problemy'), ('wordpress_http_503', 'WordPress'),
    ('llm_http_418', 'HTTP 418'), ('nieznany_kod', 'nieznany_kod'),
])
def test_unknown_codes_still_get_readable_message(code, fragment):
    assert fragment in public_error_message(code)


def test_legacy_message_is_replaced_but_specific_messages_stay():
    assert 'OPENAI_API_KEY' in readable_error_message('llm_http_401', LEGACY_PREFIX + 'llm_http_401')
    assert readable_error_message('invalid_output', 'Nieprawidłowy raport QA: x') == 'Nieprawidłowy raport QA: x'
    assert readable_error_message(None, None) is None


def test_missing_api_key_has_own_code():
    assert LLMNotConfiguredError('missing').code == 'llm_not_configured'
