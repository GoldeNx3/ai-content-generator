# Rola pliku: Zadanie `feedback.suggest`: płatna analiza poprawek redaktora i powodów odrzuceń jednego tematu.
# Zwraca propozycje zasad stylu i zakazanych zwrotów, pomijając te, które już są w profilu redakcji.

from pydantic import BaseModel, Field

from ai.context import TaskContext
from ai.errors import TaskInputError
from app.schemas.editorial import EditorialProfile
from app.services.feedback.diff import changed_passages
from app.services.llm.feedback import build_feedback_prompt

MAX_BANNED_PHRASE = 80


class FeedbackInput(BaseModel):
    title: str = Field(max_length=1000)
    original: str = Field(default="", max_length=80000)
    edited: str = Field(default="", max_length=80000)
    rejections: list[str] = Field(default_factory=list, max_length=10)
    editorial: EditorialProfile | None = None


def _known(profile: EditorialProfile | None) -> set[str]:
    if profile is None:
        return set()
    return {item.strip().casefold() for item in [*profile.banned_phrases, *profile.style_rules]}


async def run(data: dict, ctx: TaskContext) -> dict:
    payload = FeedbackInput.model_validate(data)
    passages = changed_passages(payload.original, payload.edited) if payload.original and payload.edited else []
    rejections = [reason.strip()[:1000] for reason in payload.rejections if reason.strip()]
    if not passages and not rejections:
        raise TaskInputError("Brak poprawek i powodów odrzucenia do analizy.", code="nothing_to_learn")
    prompt = build_feedback_prompt(payload.title, passages, rejections, payload.editorial)
    provider = ctx.providers["feedback"]
    result = await ctx.call("learning_feedback", lambda: provider.suggest(prompt))
    known = _known(payload.editorial)
    suggestions = []
    for suggestion in result.suggestions:
        key = suggestion.text.strip().casefold()
        if key in known or (suggestion.kind == "banned_phrase" and len(suggestion.text.strip()) > MAX_BANNED_PHRASE):
            continue
        known.add(key)
        suggestions.append({"kind": suggestion.kind, "text": suggestion.text.strip(), "why": suggestion.why.strip()})
    return {"suggestions": suggestions, "passages": len(passages)}
