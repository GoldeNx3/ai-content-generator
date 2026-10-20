# Rola pliku: Rejestr zadań AI; nazwa zadania z wejścia wybiera funkcję `run(input, ctx)`.

from ai.tasks import classify, research

TASKS = {
    "classify": classify.run,
    "research.extract": research.extract,
    "research.discover": research.discover,
    "research.analyse": research.analyse,
}
