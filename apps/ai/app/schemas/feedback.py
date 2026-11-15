# Rola pliku: Schemat odpowiedzi LLM dla pętli zwrotnej redaktora: propozycje zasad stylu i zakazanych zwrotów.

from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr


class StyleSuggestion(BaseModel):
    kind: Literal["style_rule", "banned_phrase"]
    text: str = Field(min_length=1, max_length=200)
    why: str = Field(min_length=1, max_length=300)


class FeedbackSuggestions(BaseModel):
    suggestions: list[StyleSuggestion] = Field(max_length=8)
    _usage: dict[str, str | int] | None = PrivateAttr(default=None)
