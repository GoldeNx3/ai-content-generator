# Rola pliku: Jawne błędy kolejki, niezależne od HTTP i tekstu komunikatu.

class JobConflict(Exception):
    def __init__(self, code: str, job_id=None) -> None:
        self.code = code
        self.job_id = job_id
        super().__init__(code)


class LeaseLostError(Exception):
    """Próba nie ma już prawa zapisywać danych; worker musi ją zatrzymać."""


class JobInputError(Exception):
    def __init__(self, message: str, status_code: int = 409) -> None:
        self.status_code = status_code
        super().__init__(message)
