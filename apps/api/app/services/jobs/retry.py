# Rola pliku: Błędy przejściowe i opóźnienia ponowień, bez zgadywania po tekście.

import random
from sqlalchemy.exc import OperationalError
from app.services.llm.base import LLMError
from app.services.wordpress.errors import WordPressError


def failure(exc, attempt_number):
    retryable = isinstance(exc, (OperationalError, TimeoutError)) or (
        isinstance(exc, (LLMError, WordPressError)) and exc.retryable)
    code = getattr(exc, 'code', 'timeout' if isinstance(exc, TimeoutError) else 'execution_failed')
    delay = (15 if attempt_number == 1 else 60) + random.uniform(0, 5)
    retry_after = getattr(exc, 'retry_after', None)
    if retry_after is not None:
        delay = max(delay, min(900, max(15, retry_after)))
    return code, retryable, delay
