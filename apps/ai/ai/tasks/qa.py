# Rola pliku: Zadanie `qa.evaluate`: kontrola faktów i jakości zamrożonej wersji artykułu (walidacja odwołań,
# czytelność, ocena LLM, wyliczenie wyników i progu zaliczenia). Snapshot wejścia buduje Laravel.

from typing import Any

from pydantic import BaseModel

from ai.context import TaskContext
from app.schemas.qa import QAOutput
from app.services.article.readability import readability_issues
from app.services.qa.validation import calculate_scores, validate_output, validate_references


class QaInput(BaseModel):
    snapshot: dict[str, Any]
    pass_score: int


async def evaluate(data: dict, ctx: TaskContext) -> dict:
    payload = QaInput.model_validate(data)
    snapshot = payload.snapshot
    reference_issues = validate_references(snapshot) + readability_issues(snapshot["article"]["lead"],
                                                                        snapshot["article"]["content"])
    qa = ctx.providers["qa_article"]
    result = await ctx.call("fact_checking", lambda: qa.evaluate(snapshot))
    checked = validate_output(QAOutput.model_validate(result.output), snapshot, reference_issues)
    scores = calculate_scores(checked, payload.pass_score)
    return {
        **{name: (int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value)
           for name, value in scores.items()},
        "summary": checked.summary,
        "claims": [claim.model_dump(mode="json") for claim in checked.claims],
        "issues": [issue.model_dump(mode="json") for issue in checked.issues],
    }
