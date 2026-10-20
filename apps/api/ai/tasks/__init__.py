# Rola pliku: Rejestr zadań AI; nazwa zadania z wejścia wybiera funkcję `run(input, ctx)`.

from ai.tasks import classify

TASKS = {
    "classify": classify.run,
}
