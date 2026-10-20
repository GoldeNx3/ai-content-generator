# Rola pliku: Schematy danych source: Pydantic waliduje dane wejścia/wyjścia; te klasy nie tworzą tabel SQL.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.enums import SourceType


class SourceCreate(BaseModel):
    # Field dodaje walidację Pydantic: ge/le to granice liczb, a default/default_factory określają
    # wartość domyślną.
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    type: SourceType = SourceType.RSS
    active: bool = True


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: HttpUrl | None = None
    active: bool | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: SourceType
    url: str
    active: bool
    last_fetched_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FetchResult(BaseModel):
    sources_processed: int = 0
    items_found: int = 0
    new_candidates: int = 0
    duplicates: int = 0
    skipped_old: int = 0
    errors: int = 0

    def add(self, other: "FetchResult") -> None:
        self.sources_processed += other.sources_processed
        self.items_found += other.items_found
        self.new_candidates += other.new_candidates
        self.duplicates += other.duplicates
        self.skipped_old += other.skipped_old
        self.errors += other.errors
