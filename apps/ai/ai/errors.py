# Rola pliku: Zamiana wyjątków zadań AI na kody błędów kontraktu (code, message, retryable, retry_after),
# które Laravel zapisuje w jobie i według których decyduje o ponowieniu.

from pydantic import ValidationError

from app.services.jobs.errors import JobInputError
from app.services.jobs.messages import public_error_message
from app.services.llm.base import LLMError


class TaskInputError(Exception):
    """Nieprawidłowe wejście od Laravela: błąd programistyczny, bez ponawiania."""

    def __init__(self, message: str, code: str = "invalid_input") -> None:
        super().__init__(message)
        self.code = code


def describe(exc: BaseException) -> dict:
    if isinstance(exc, LLMError):
        return {"code": exc.code, "message": public_error_message(exc.code), "retryable": exc.retryable,
                "retry_after": exc.retry_after}
    if isinstance(exc, TaskInputError):
        return {"code": exc.code, "message": str(exc), "retryable": False, "retry_after": None}
    if isinstance(exc, JobInputError):
        # Walidacja wyniku modelu (np. poprawka Auto Fix bez pokrycia w faktach): bez ponawiania.
        return {"code": "invalid_output", "message": str(exc), "retryable": False, "retry_after": None}
    if isinstance(exc, ValidationError):
        return {"code": "invalid_input", "message": str(exc), "retryable": False, "retry_after": None}
    public = getattr(exc, "public_message", None)
    code = getattr(exc, "code", None) or "execution_failed"
    retryable = bool(getattr(exc, "retryable", False))
    return {"code": code, "message": public or public_error_message(code), "retryable": retryable,
            "retry_after": getattr(exc, "retry_after", None)}
