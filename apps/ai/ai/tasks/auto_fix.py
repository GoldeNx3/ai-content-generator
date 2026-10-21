# Rola pliku: Zadanie `autofix.fix`: poprawki LLM dla wskazanych issues QA, dosłowne zastosowanie łatek
# z walidacją (pokrycie w faktach, jednoznaczność, limit zmian). Nową wersję zapisuje Laravel.

from typing import Any

from pydantic import BaseModel

from ai.context import TaskContext
from app.schemas.auto_fix import FixOutput
from app.services.auto_fix.payload import llm_payload
from app.services.auto_fix.validation import apply_fixes


class FixInput(BaseModel):
    payload: dict[str, Any]
    max_change_ratio: float


async def fix(data: dict, ctx: TaskContext) -> dict:
    request = FixInput.model_validate(data)
    narrowed = llm_payload(request.payload)
    fixer = ctx.providers["auto_fix_article"]
    result = await ctx.call("fixing_article", lambda: fixer.fix(narrowed))
    output = FixOutput.model_validate(result.output)
    applied = apply_fixes(narrowed, output, request.max_change_ratio)
    original = request.payload["article"]
    changed = any(applied.article[key] != original[key] for key in applied.article)
    return {
        "summary": output.summary,
        "fix_results": [r.model_dump(mode="json") for r in output.fix_results],
        "issues_fixed": sum(r.status == "fixed" for r in output.fix_results),
        "issues_skipped": sum(r.status == "skipped" for r in output.fix_results),
        "change_ratio": round(applied.change_ratio, 6),
        "changes": applied.changes,
        "warnings": applied.warnings,
        "changed": changed,
        "article": {k: v for k, v in applied.article.items() if k not in ("sections", "lead_fact_ids")},
        "lead_fact_ids": sorted(set(original.get("lead_fact_ids", []))
                                | {i for p in output.patches if p.field == "lead" for i in p.fact_ids}),
        "patches": [p.model_dump(mode="json") for p in output.patches],
    }
