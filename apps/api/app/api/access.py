# Rola pliku: Centralna kontrola własności zasobów. Zależność routera chronionego: dla każdego ID
# w ścieżce (candidate_id, article_id, job_id, ...) ustala workspace właściciela i zwraca 404, gdy zasób
# nie należy do workspace'u zalogowanego użytkownika. Listy i agregaty filtrują jawnie w endpointach.

from collections.abc import Callable
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import Select, select

from app.api.deps import CurrentUserDep, SessionDep
from app.models import Article, ArticleFix, Candidate, Source
from app.models.job import Job


def _article_workspace(article_id: int) -> Select:
    return select(Candidate.workspace_id).join(Article, Article.candidate_id == Candidate.id).where(Article.id == article_id)


# Parametr ścieżki -> (konwersja, zapytanie o workspace właściciela). Nowa nazwa ID w trasie musi trafić
# tutaj; test_workspace_isolation.py sprawdza, że żadna chroniona trasa jej nie pomija.
OWNERSHIP: dict[str, tuple[Callable[[str], object], Callable[..., Select]]] = {
    "candidate_id": (int, lambda value: select(Candidate.workspace_id).where(Candidate.id == value)),
    "source_id": (int, lambda value: select(Source.workspace_id).where(Source.id == value)),
    "article_id": (int, _article_workspace),
    "version_id": (int, _article_workspace),
    "fix_id": (int, lambda value: select(Candidate.workspace_id)
               .join(Article, Article.candidate_id == Candidate.id)
               .join(ArticleFix, ArticleFix.source_article_version_id == Article.id)
               .where(ArticleFix.id == value)),
    "job_id": (UUID, lambda value: select(Job.workspace_id).where(Job.id == value)),
}


async def enforce_workspace(request: Request, current: CurrentUserDep, session: SessionDep) -> None:
    for name, raw in request.path_params.items():
        if name not in OWNERSHIP:
            continue
        convert, query = OWNERSHIP[name]
        try:
            value = convert(raw)
        except ValueError:
            # Zły format ID: trasa sama zwróci 422 przy walidacji parametru.
            continue
        owner = await session.scalar(query(value))
        if owner != current.workspace_id:
            # Ten sam kod dla cudzego i nieistniejącego zasobu: nie ujawniamy, że ID istnieje.
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found"})
