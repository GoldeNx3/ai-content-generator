# Rola pliku: Pobieranie pojedynczego źródła i zapis wyniku w obiekcie ORM.
# Ta klasa nie zatwierdza transakcji. O momencie commit decyduje wywołujący
# serwis lub pipeline, dzięki czemu granice zapisu pozostają widoczne.

import logging

from app.core.config import Settings
from app.models import FetchStatus, ResearchSource
from app.services.research.content_extractor import ContentExtractor, ExtractedDocument, ExtractionError
from app.services.research.source_scoring import assess_source

logger = logging.getLogger(__name__)


class ResearchSourceLoader:
    """Pobiera treść i aktualizuje pola źródła; błąd strony staje się statusem failed."""

    def __init__(self, extractor: ContentExtractor, settings: Settings) -> None:
        self.extractor = extractor
        self.settings = settings

    # Błąd jednego URL-a zamieniamy na wynik ExtractionError, aby dało się zapisać nieudane źródło i
    # kontynuować.
    async def extract_safely(self, url: str) -> ExtractedDocument | ExtractionError:
        try:
            return await self.extractor.extract(url)
        except ExtractionError as exc:
            return exc
        except Exception as exc:  # błąd parsera nie przerywa całego researchu
            logger.exception("Unexpected extraction error url=%s", url)
            return ExtractionError(f"Extraction failed: {exc.__class__.__name__}")

    async def fetch_into(self, source: ResearchSource, official: set[str], candidate_id: int, research_id: int) -> None:
        self.apply_extraction(source, await self.extract_safely(source.url), official, candidate_id, research_id)

    def apply_extraction(
        self,
        source: ResearchSource,
        extraction: ExtractedDocument | ExtractionError,
        official: set[str],
        candidate_id: int,
        research_id: int,
    ) -> None:
        assessment = assess_source(source.url, official)
        source.source_type, source.source_score = assessment.source_type, assessment.score
        if isinstance(extraction, ExtractionError):
            source.fetch_status = FetchStatus.FAILED
            source.http_status = extraction.http_status
            source.error = str(extraction)
            logger.warning(
                "Source fetch failed candidate_id=%s research_id=%s url=%s status=%s error=%s",
                candidate_id, research_id, source.url, extraction.http_status, extraction,
            )
            return
        source.fetch_status = FetchStatus.SUCCESS
        source.http_status = extraction.http_status
        source.error = None
        source.title = (extraction.title or source.title or "")[:1000] or None
        source.publisher = clean_publisher(extraction.publisher)
        source.published_at = extraction.published_at
        source.extracted_content = extraction.content
        source.raw_content = (extraction.raw_html or "")[: self.settings.raw_content_max_chars] or None
        logger.info(
            "Source saved candidate_id=%s research_id=%s url=%s chars=%d type=%s score=%d",
            candidate_id, research_id, source.url, len(extraction.content),
            source.source_type, source.source_score,
        )


def clean_publisher(name: str | None) -> str | None:
    """Czyści nazwy wydawców z metadanych, np. Allen_Ai → Allen Ai."""
    if not name:
        return None
    name = " ".join(name.replace("_", " ").split())[:300]
    return name[0].upper() + name[1:] if name.islower() else name
