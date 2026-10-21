# Rola pliku: Wyjątki researchu. API zamienia je na HTTP 404/409/400.
# Wspólny moduł pozwala serwisowi i pipeline’owi używać tych samych wyjątków
# bez wzajemnego importowania się (cykliczne importy utrudniają start aplikacji).


class ResearchError(Exception):
    """Błąd domenowy researchu, niezależny od FastAPI."""


class NoSourceContentError(ResearchError):
    code = "no_source_content"
    public_message = (
        "Nie udało się pobrać treści żadnego źródła. "
        "Dodaj dostępne źródło ręcznie i ponów analizę "
        "lub skonfiguruj wyszukiwarkę."
    )


class CandidateNotFoundError(ResearchError):
    pass


class ResearchNotFoundError(ResearchError):
    pass


class ResearchInProgressError(ResearchError):
    pass


class DuplicateSourceError(ResearchError):
    pass
