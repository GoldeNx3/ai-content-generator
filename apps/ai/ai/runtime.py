# Rola pliku: Wykonanie jednego zadania z kontraktu JSON: wybór zadania, kontekst, mapowanie błędów.
# Wynik zawsze zawiera listę wywołań LLM, także przy błędzie, aby Laravel naliczył koszt.

import logging

from ai.context import TaskContext
from ai.errors import TaskInputError, describe
from ai.tasks import TASKS

logger = logging.getLogger("ai")


async def run(request: dict, context: TaskContext | None = None) -> dict:
    task = request.get("task")
    ctx = context or TaskContext(demo=bool(request.get("demo")))
    try:
        if task not in TASKS:
            raise TaskInputError(f"Unknown task: {task}", code="unknown_task")
        result = await TASKS[task](request.get("input") or {}, ctx)
        return {"ok": True, "result": result, "calls": ctx.calls}
    except Exception as exc:  # Każdy błąd wraca jako JSON; Laravel decyduje o ponowieniu.
        logger.exception("AI task failed task=%s", task)
        return {"ok": False, "error": describe(exc), "calls": ctx.calls}
    finally:
        await ctx.close()
