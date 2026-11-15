# Rola pliku: Profil redakcyjny konta (czytelnik, ton, zakres tematów, zakazane zwroty, wzorzec stylu).
# Przychodzi z Laravela w danych zadania; brak profilu = dotychczasowe, ogólne zachowanie.

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class EditorialProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    audience: str = Field(default="", max_length=500)
    voice: str = Field(default="", max_length=500)
    topics_scope: str = Field(default="", max_length=1000)
    banned_phrases: list[str] = Field(default_factory=list, max_length=50)
    example_post: str = Field(default="", max_length=6000)
    style_rules: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=30)
